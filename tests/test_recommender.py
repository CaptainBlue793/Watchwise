import numpy as np
import pandas as pd
import pytest
import requests

from recommender import MovieIndex, fetch_poster, load_catalog, validate_catalog


def test_starter_catalog_and_sparse_ranking():
    index = MovieIndex(load_catalog())
    seed = int(index.movies[index.movies.title == "Blade Runner"].index[0])
    results = index.recommend([seed])
    assert results[0]["title"] == "Blade Runner 2049"
    assert all(row["catalog_index"] != seed for row in results)
    assert results[0]["shared_terms"]
    assert all(0 < row["similarity"] <= 1.000001 for row in results)


def test_multiple_seeds_filters_and_exclusions():
    index = MovieIndex(load_catalog())
    rows = index.recommend([0, 1], genres=["Science Fiction"], years=(2010, 2020), max_runtime=150, excluded=[4])
    assert rows
    assert all("Science Fiction" in row["genres"] and row["runtime"] <= 150 and 2010 <= row["year"] <= 2020 for row in rows)
    assert all(row["catalog_index"] not in [0, 1, 4] for row in rows)
    assert index.recommend([0], min_rating=9) == []


def test_tmdb_csv_schema_and_duplicate_titles():
    frame = pd.DataFrame({"id": [1, 2], "title": ["Same", "Same"], "overview": ["space astronaut planet", "family friendship garden"], "release_date": ["2001-01-01", "2010-01-01"], "genres": ['[{"id": 1, "name": "Drama"}]', "Comedy|Family"], "vote_average": [8, 7]})
    movies = validate_catalog(frame)
    assert len(movies) == 2
    assert movies.genres.iloc[0] == "Drama"
    assert movies.year.tolist() == [2001, 2010]


@pytest.mark.parametrize("data", [b"", b"name\nMovie", b"title,overview\nOnly,one movie"])
def test_invalid_catalog_is_actionable(data):
    with pytest.raises(ValueError):
        load_catalog(data)


def test_bad_metadata_is_unknown_not_a_crash():
    frame = pd.DataFrame({"title": ["One", "Two"], "overview": ["space ship", "space planet"], "year": [np.inf, "unknown"], "runtime": [-1, 80], "rating": [99, 8]})
    movies = validate_catalog(frame)
    assert movies.year.isna().all()
    assert pd.isna(movies.rating.iloc[0])


def test_missing_key_and_network_failure_are_harmless():
    def broken(*args, **kwargs):
        raise requests.Timeout()
    assert fetch_poster(1, "") is None
    assert fetch_poster(1, "test", broken) is None


def test_valid_poster_response_and_timeout():
    calls = []
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"poster_path": "/poster.jpg"}
    def get(*args, **kwargs):
        calls.append(kwargs)
        return Response()
    assert fetch_poster(1, "test", get).endswith("/poster.jpg")
    assert calls[0]["timeout"] == 5


def test_empty_or_malicious_poster_path_is_ignored():
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"poster_path": "//bad.example/image.jpg"}
    assert fetch_poster(1, "test", lambda *args, **kwargs: Response()) is None
