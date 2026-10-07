# WatchWise

A movie discovery workspace that starts without missing pickle files, model downloads, or an API key. Choose up to five favorites and discover films with related descriptions and genres.

## What's inside

- A 32-film starter catalog with authored descriptions, genres, years, and approximate runtimes.
- Sparse TF-IDF content ranking across several favorites, without allocating an all-movies similarity matrix.
- Shared-term explanations and explicit content-similarity scores.
- Genre, year, runtime, and rating filters; optional exclusion of saved movies.
- Catalog search, a browser-session watchlist, and CSV exports of picks and saved films.
- Validated UTF-8 CSV imports, including TMDB-shaped genre JSON and release dates.
- Optional cached poster lookup with bounded network timeouts and graceful missing-artwork fallback.

## Run locally with starGPU

From this directory in PowerShell:

```powershell
conda activate starGPU
python -m pip install -r requirements.txt
python -m streamlit run Watchwise.py --server.port 8503
```

Alternatively, `./run.ps1` uses `conda run -n starGPU`. Open http://localhost:8503. No GPU is required. The theme lives in `.streamlit/config.toml`.

## Bring your catalog

Upload a CSV in the sidebar, or download the sample format from the app. Required columns: `title`, `overview`. Optional columns:

| Column | Format |
| --- | --- |
| `movie_id` or `id` | Numeric TMDB movie ID, only needed for poster lookup |
| `genres` | `Science Fiction|Adventure`, comma-separated names, or a JSON list of TMDB genre objects |
| `year` or `release_date` | Release year or a parseable release date |
| `rating` or `vote_average` | Catalog rating from 0 to 10 |
| `runtime` | Runtime in minutes |
| `tags` | Additional descriptive terms |

Movies with different years remain distinct even if titles match. Exact title/year duplicates collapse. Invalid numeric metadata becomes unknown. Active numeric filters exclude movies with unknown values; the starter catalog intentionally omits ratings. Ratings are source metadata, not WatchWise's evaluation.

Imports are limited to 20 MB and 50,000 movies, with at least two distinct titles/year combinations and meaningful descriptions. Keep descriptions/tags below 20,000 characters per row. Uploading a new catalog clears that session's recommendations and watchlist so row identifiers cannot refer to the wrong movies.

The historical `Movie_Recommender.ipynb` remains as a training reference. The app no longer loads pickle files. To reuse that notebook's output, export its title/overview/tags metadata to CSV; no precomputed `similarity.pkl` is needed.

## Optional posters

Set a TMDB API key before starting the app:

```powershell
$env:TMDB_API_KEY = 'your-key'
python -m streamlit run Watchwise.py --server.port 8503
```

`.env.example` documents the variable; `.env` files are not loaded automatically. The old embedded credential has been removed from the application. Artwork requests send only movie IDs to TMDB; API failures and missing images use a placeholder. Without a key, the application makes no poster requests.

This product uses the TMDB API but is not endorsed or certified by TMDB. Follow [TMDB attribution requirements](https://developer.themoviedb.org/docs/faq) if deploying a version that uses its artwork.

## Understanding your results

Recommendations rank the cosine similarity between a movie's TF-IDF description/genres and the average profile of selected favorites. Shared terms identify contributing features. A score measures content overlap, not a predicted user rating or confidence. Movies with no shared features are omitted. Results remain those of the last search until you search again.

Watchlists last for the current browser app session; download one to preserve it. CSV catalog data is processed in memory. Legacy background assets, `font.css`, and root `config.toml` remain unused by the new interface.

## Checks

```powershell
python -m pip install pytest
python -m pytest tests -q
```

Tests cover sparse ranking, multi-favorite profiles, filters, exclusions, CSV validation, duplicate titles, poster failures, and app save/remove interactions.
