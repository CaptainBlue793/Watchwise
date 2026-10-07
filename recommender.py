"""Validated movie catalogs and sparse, explainable content recommendations."""
from io import BytesIO
import json
from pathlib import Path
import re

import numpy as np
import pandas as pd
import requests
from sklearn.feature_extraction.text import TfidfVectorizer


def genre_names(value):
    if isinstance(value, list):
        return "|".join(str(item.get("name", "")) if isinstance(item, dict) else str(item) for item in value)
    text = str(value).strip()
    if text.startswith("["):
        try:
            return genre_names(json.loads(text))
        except (TypeError, ValueError):
            raise ValueError("Genres must be a JSON list or names separated with |.")
    return "|".join(part.strip() for part in re.split(r"[|,]", text) if part.strip())


def validate_catalog(frame):
    frame = frame.copy().rename(columns={"id": "movie_id", "vote_average": "rating"})
    if not {"title", "overview"}.issubset(frame.columns):
        raise ValueError("Your CSV needs title and overview columns. Optional: movie_id, genres, year, rating, runtime, tags.")
    if not 2 <= len(frame) <= 50_000:
        raise ValueError("Use a catalog with 2–50,000 movies.")
    if frame.columns.duplicated().any():
        raise ValueError("Catalog has duplicate column names; keep one ID and one rating column.")
    for column in ["title", "overview", "tags"]:
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str).str.strip()
    if (frame["title"] == "").any():
        raise ValueError("Every movie needs a title.")
    if frame["overview"].str.len().max() > 20_000 or frame["tags"].str.len().max() > 20_000:
        raise ValueError("Use descriptions and tags shorter than 20,000 characters per movie.")
    if "year" not in frame and "release_date" in frame:
        frame["year"] = pd.to_datetime(frame["release_date"], errors="coerce").dt.year
    for column in ["year", "rating", "runtime", "movie_id"]:
        if column not in frame:
            frame[column] = np.nan
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame.loc[~np.isfinite(frame[column]), column] = np.nan
    for column, low, high in [("year", 1880, 2200), ("rating", 0, 10), ("runtime", 1, 1000), ("movie_id", 1, 2**53)]:
        frame.loc[~frame[column].between(low, high), column] = np.nan
    frame["genres"] = frame.get("genres", pd.Series("", index=frame.index)).fillna("").apply(genre_names)
    if not (frame["overview"].str.len() > 0).any():
        raise ValueError("Add at least one movie overview to build content recommendations.")
    # Duplicate title/year records collapse; remakes with different years remain distinct.
    frame = frame.drop_duplicates(subset=["title", "year"]).reset_index(drop=True)
    if len(frame) < 2:
        raise ValueError("Add at least two distinct movies to your catalog.")
    return frame


def load_catalog(data=None):
    if data is None:
        return validate_catalog(pd.read_csv(Path(__file__).with_name("data") / "movies.csv"))
    if len(data) > 20 * 1024 * 1024:
        raise ValueError("Choose a CSV smaller than 20 MB.")
    try:
        return validate_catalog(pd.read_csv(BytesIO(data)))
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as exc:
        raise ValueError("Could not read that CSV. Save it as a UTF-8 CSV with headers.") from exc


class MovieIndex:
    def __init__(self, frame):
        self.movies = validate_catalog(frame)
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=25_000, sublinear_tf=True)
        corpus = (self.movies["overview"] + " " + self.movies["tags"] + " " + self.movies["genres"].str.replace("|", " ", regex=False) * 2)
        try:
            self.matrix = self.vectorizer.fit_transform(corpus)
        except ValueError as exc:
            raise ValueError("Movie descriptions need meaningful words to build recommendations.") from exc
        self.terms = self.vectorizer.get_feature_names_out()

    def recommend(self, seeds, count=8, genres=None, years=None, min_rating=0.0, max_runtime=None, excluded=None):
        seeds = list(dict.fromkeys(seeds))
        if not seeds or any(not isinstance(i, (int, np.integer)) or not 0 <= i < len(self.movies) for i in seeds):
            raise ValueError("Choose at least one movie from this catalog.")
        if not 1 <= count <= 24:
            raise ValueError("Choose 1–24 recommendations.")
        profile = np.asarray(self.matrix[seeds].mean(axis=0)).ravel()
        norm = np.linalg.norm(profile)
        if norm:
            profile /= norm
        scores = np.asarray(self.matrix @ profile).ravel()
        candidates = self.movies.copy()
        mask = ~candidates.index.isin(set(seeds) | set(excluded or []))
        if genres:
            mask &= candidates["genres"].apply(lambda value: bool(set(value.split("|")) & set(genres)))
        if years:
            mask &= candidates["year"].between(*years)
        if min_rating > 0:
            mask &= candidates["rating"] >= min_rating
        if max_runtime:
            mask &= candidates["runtime"] <= max_runtime
        mask &= scores > 0
        candidates["similarity"] = scores
        candidates["catalog_index"] = candidates.index
        ranked = candidates[mask].sort_values(["similarity", "rating", "title"], ascending=[False, False, True], na_position="last").head(count)
        result = []
        for index, row in ranked.iterrows():
            shared = self.matrix[index].multiply(profile).toarray().ravel()
            terms = [self.terms[i] for i in np.argsort(shared)[::-1] if shared[i] > 0][:5]
            item = row.to_dict()
            item["shared_terms"] = terms
            result.append(item)
        return result


def fetch_poster(movie_id, api_key, get=requests.get):
    if not api_key or pd.isna(movie_id):
        return None
    try:
        response = get(f"https://api.themoviedb.org/3/movie/{int(movie_id)}", params={"api_key": api_key}, timeout=5)
        response.raise_for_status()
        data = response.json()
        path = data.get("poster_path") if isinstance(data, dict) else None
        if isinstance(path, str) and re.fullmatch(r"/[A-Za-z0-9_.-]+", path):
            return "https://image.tmdb.org/t/p/w500" + path
    except (requests.RequestException, ValueError, TypeError):
        pass
    return None
