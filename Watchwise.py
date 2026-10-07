"""WatchWise: an offline-first movie discovery workspace."""
import hashlib
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from recommender import MovieIndex, fetch_poster, load_catalog


@st.cache_resource(max_entries=4, show_spinner=False)
def build_index(data):
    return MovieIndex(load_catalog(data))


@st.cache_data(ttl=86400, max_entries=500, show_spinner=False)
def poster(movie_id, api_key):
    return fetch_poster(movie_id, api_key)


def main():
    st.set_page_config(page_title="WatchWise · Find your next film", page_icon="🎬", layout="wide")
    st.markdown(f"<style>{Path(__file__).with_name('style.css').read_text()}</style>", unsafe_allow_html=True)
    st.caption("WATCHWISE / YOUR NEXT GREAT WATCH")
    st.title("Good taste deserves a sequel.")
    st.write("Pick a few films you love. Discover what to watch next, and why it fits.")
    with st.sidebar:
        st.header("Your movie library")
        upload = st.file_uploader("Use your own catalog", type=["csv"])
        st.caption("CSV needs title and overview. Add genres, year, rating, runtime, and movie_id for richer discovery.")
        st.download_button("Download example catalog", (Path(__file__).with_name("data") / "movies.csv").read_bytes(), "movies.csv", "text/csv")
    data = upload.getvalue() if upload is not None else None
    try:
        index = build_index(data)
    except ValueError as exc:
        st.error(str(exc))
        return
    movies = index.movies
    catalog_id = hashlib.sha256(data).hexdigest() if data else "demo-v1"
    if st.session_state.get("catalog_id") != catalog_id:
        st.session_state.update({"catalog_id": catalog_id, "watchlist": [], "results": [], "seeds": [], "searched": False, "seed_description": ""})
    api_key = os.environ.get("TMDB_API_KEY", "").strip()
    with st.sidebar:
        st.divider()
        st.header("Fine-tune your picks")
        genres = st.multiselect("Genres", sorted({g for row in movies["genres"] for g in row.split("|") if g}))
        year_values = movies["year"].dropna()
        years = None
        if not year_values.empty and year_values.min() < year_values.max():
            if st.checkbox("Filter release years"):
                years = st.slider("Release years", int(year_values.min()), int(year_values.max()), (int(year_values.min()), int(year_values.max())))
        min_rating = st.slider("Minimum catalog rating", 0.0, 10.0, 0.0, 0.5)
        max_runtime = st.slider("Maximum runtime (minutes)", 60, 240, 150) if st.checkbox("Limit runtime") else None
        count = st.slider("Number of recommendations", 4, 24, 8)
        hide_saved = st.checkbox("Hide saved movies", value=True)
        st.caption("Content similarity measures shared descriptions and genres. It is not a prediction of your rating.")
        if not api_key:
            st.caption("Poster artwork is optional. Configure TMDB_API_KEY to enable it.")
        else:
            st.caption("Poster lookup uses TMDB and sends movie IDs to its API.")
    metrics = st.columns(3)
    metrics[0].metric("Films in your library", len(movies))
    metrics[1].metric("Genres to explore", len({g for row in movies["genres"] for g in row.split("|") if g}))
    metrics[2].metric("Saved for later", len(st.session_state["watchlist"]))

    def movie_label(i):
        movie = movies.iloc[i]
        year = f"{int(movie['year'])}" if pd.notna(movie["year"]) else "year unknown"
        return f"{movie['title']} ({year}) · #{i + 1}"

    seeds = st.multiselect("Films you love", list(range(len(movies))), format_func=movie_label, key="seeds", max_selections=5, placeholder="Search for a title…")
    if st.button("Find my next watch", type="primary", disabled=not seeds):
        with st.spinner("Finding shared stories, themes, and genres…"):
            results = index.recommend(seeds, count, genres, years, min_rating, max_runtime, st.session_state["watchlist"] if hide_saved else [])
            st.session_state["results"] = results
            st.session_state["searched"] = True
            st.session_state["seed_description"] = ", ".join(str(movies.iloc[i]["title"]) for i in seeds)
    discovery, saved, library = st.tabs(["Discover", "Your watchlist", "Browse library"])

    def card(row, slot, prefix):
        movie_index = int(row["catalog_index"])
        with slot, st.container(border=True):
            artwork = poster(row["movie_id"], api_key) if api_key else None
            if artwork:
                st.image(artwork, use_container_width=True)
            else:
                st.markdown('<div class="poster-placeholder">▶<br><small>WATCHWISE</small></div>', unsafe_allow_html=True)
            st.subheader(str(row["title"]))
            year = str(int(row["year"])) if pd.notna(row["year"]) else "Year unknown"
            runtime = f"{int(row['runtime'])} min" if pd.notna(row["runtime"]) else "Runtime unknown"
            st.caption(f"{year} · {runtime}")
            st.write(str(row["genres"]).replace("|", " · "))
            st.write(str(row["overview"]))
            if pd.notna(row["rating"]):
                st.caption(f"Catalog rating: {row['rating']:.1f}/10")
            if "similarity" in row:
                st.caption(f"Content similarity: {row['similarity']:.0%}")
                st.caption("Shared themes: " + ", ".join(row["shared_terms"]))
            is_saved = movie_index in st.session_state["watchlist"]
            if st.button("Remove from watchlist" if is_saved else "Save for later", key=f"{prefix}-{movie_index}", use_container_width=True):
                if is_saved:
                    st.session_state["watchlist"].remove(movie_index)
                else:
                    st.session_state["watchlist"].append(movie_index)
                st.rerun()

    with discovery:
        results = st.session_state.get("results", [])
        if results:
            st.caption(f"Inspired by {st.session_state.get('seed_description', '')}. Results reflect your last search.")
            visible = [row for row in results if not hide_saved or row["catalog_index"] not in st.session_state["watchlist"]]
            for start in range(0, len(visible), 4):
                slots = st.columns(4)
                for slot, row in zip(slots, visible[start:start + 4]):
                    card(row, slot, "discover")
            if not visible:
                st.info("All these picks are saved. Search again for more movies.")
            export = pd.DataFrame(results).drop(columns=["catalog_index"], errors="ignore")
            st.download_button("Download recommendations", export.to_csv(index=False), "watchwise-picks.csv", "text/csv")
        elif st.session_state.get("searched"):
            st.info("No movies match these preferences. Broaden the filters or choose different favorites.")
        else:
            st.info("Select a favorite above to start. Your catalog is ready; no API key or model download is needed.")
    with saved:
        watchlist = st.session_state["watchlist"]
        if not watchlist:
            st.info("Save a discovery to build your next movie night.")
        for start in range(0, len(watchlist), 4):
            slots = st.columns(4)
            for slot, i in zip(slots, watchlist[start:start + 4]):
                row = movies.iloc[i].to_dict()
                row["catalog_index"] = i
                card(row, slot, "saved")
        if watchlist:
            st.download_button("Download watchlist", movies.iloc[watchlist].to_csv(index=False), "watchwise-watchlist.csv", "text/csv")
        st.caption("Your watchlist stays in this browser session. Download it to keep a copy.")
    with library:
        search = st.text_input("Search the library")
        filtered = movies[movies["title"].str.contains(search, case=False, regex=False)] if search else movies
        st.dataframe(filtered[["title", "year", "genres", "runtime", "rating"]], hide_index=True, use_container_width=True)
        if data is None:
            st.caption("Starter catalog: hand-written descriptions and approximate runtimes. Ratings are omitted; import a catalog with ratings to use that filter.")
    if api_key:
        with st.expander("Credits"):
            st.image("https://www.themoviedb.org/assets/2/v4/logos/v2/blue_short-8e7b30f73a4020692ccca9c88bafe5dcb6f8a62a4c6bc55cd9ba82bb2cd95f6c.svg", width=120)
            st.caption("This product uses the TMDB API but is not endorsed or certified by TMDB.")
            st.markdown("Artwork provided by [The Movie Database](https://www.themoviedb.org).")


if __name__ == "__main__":
    main()
