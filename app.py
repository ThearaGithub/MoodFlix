from pathlib import Path

import pandas as pd
import streamlit as st

from src.data_loader import load_catalog, load_ratings
from src.extras import get_movie_extras
from src.mood import MOOD_EMOJI, MOOD_GENRES
from src.recommender import recommend
from src.ui import cast_grid, inject_css, movie_card, poster_grid, trailer_block

LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.jpe"

st.set_page_config(
    page_title="MoodFlix",
    page_icon=str(LOGO_PATH),
    layout="wide",
)
inject_css()

PAGES = ["Home", "Discover", "Search", "Watchlist", "Insights", "About"]
TEAM = ["Khon Sotheara", "Cheang Youpheng", "Chea Sela", "Khann Udomvirak"]


def go_to(page_name):
    st.session_state.nav = page_name


if "nav" not in st.session_state:
    st.session_state.nav = "Home"
if "liked" not in st.session_state:
    st.session_state.liked = []
if "disliked" not in st.session_state:
    st.session_state.disliked = []
if "watchlist" not in st.session_state:
    st.session_state.watchlist = []
if "queue" not in st.session_state:
    st.session_state.queue = []
if "seen" not in st.session_state:
    st.session_state.seen = []
if "fresh_batch" not in st.session_state:
    st.session_state.fresh_batch = False
if "search_page" not in st.session_state:
    st.session_state.search_page = 1
if "search_key" not in st.session_state:
    st.session_state.search_key = ""
if "mood" not in st.session_state:
    st.session_state.mood = "Happy"


try:
    catalog = load_catalog()
    ratings = load_ratings()
except FileNotFoundError:
    st.error(
        "Movie data was not found. Run `python scripts/download_data.py` "
        "and then refresh this page."
    )
    st.stop()


def movie_by_id(movie_id):
    match = catalog[catalog["movieId"] == movie_id]
    return match.iloc[0] if not match.empty else None


def add_to_watchlist(movie_id):
    if movie_id not in st.session_state.watchlist:
        st.session_state.watchlist.append(movie_id)


def refresh_queue():
    # Movies already dealt out in the deck count as seen, so a refresh
    # serves a genuinely fresh batch instead of the same top results.
    for movie_id in st.session_state.queue:
        if movie_id not in st.session_state.seen:
            st.session_state.seen.append(movie_id)

    recommendations = recommend(
        catalog,
        ratings,
        st.session_state.liked,
        st.session_state.disliked,
        mood=st.session_state.mood,
        n=20,
        exclude_ids=st.session_state.seen,
        randomize=True,
    )
    st.session_state.queue = recommendations["movieId"].tolist()


def reset_queue():
    st.session_state.queue = []


@st.dialog("Movie details", width="large")
def show_movie_details(movie):
    movie_card(movie)

    year_value = movie.get("year")
    year_value = (
        int(year_value)
        if year_value is not None and pd.notna(year_value)
        else None
    )
    tmdb_value = movie.get("tmdbId")
    tmdb_value = (
        int(tmdb_value)
        if tmdb_value is not None and pd.notna(tmdb_value)
        else None
    )
    imdb_value = movie.get("imdbId")
    imdb_value = (
        str(imdb_value)
        if imdb_value is not None and pd.notna(imdb_value)
        else ""
    )

    with st.spinner("Loading trailer and cast…"):
        extras = get_movie_extras(
            tmdb_value,
            imdb_value,
            str(movie.get("title", "")),
            year_value,
        )

    st.divider()
    st.subheader("Trailer")
    trailer_block(extras.get("trailer"))

    st.subheader("Cast")
    cast_grid(extras.get("cast") or [])

    source = extras.get("source")
    if source == "TMDB":
        st.caption("Trailer and cast via TMDB.")
    elif source == "web":
        st.caption("Trailer via YouTube · Cast via Wikipedia/Wikidata.")

    movie_id = int(movie["movieId"])
    if movie_id in st.session_state.watchlist:
        st.caption("✓ Already in your watchlist.")
    else:
        st.button(
            "➕ Add to watchlist",
            key=f"dialog_add_{movie_id}",
            on_click=add_to_watchlist,
            args=(movie_id,),
        )


with st.sidebar:
    st.image(str(LOGO_PATH), width=96)
    st.title("MoodFlix")
    st.caption("Mood-first movie discovery")
    st.radio("Navigate", PAGES, key="nav")
    st.divider()
    st.metric("Liked", len(st.session_state.liked))
    st.metric("Watchlist", len(st.session_state.watchlist))

page = st.session_state.nav

if page == "Home":
    st.title("Find a movie that fits your mood.")
    st.write(
        "MoodFlix learns from the movies you like, blends content, rating, "
        "popularity, and collaborative signals, and serves a swipeable shortlist."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Movies", f"{len(catalog):,}")
    with col2:
        st.metric("Ratings", f"{len(ratings):,}")
    with col3:
        st.metric("Genres", catalog["genres"].str.get_dummies(sep="|").shape[1])
    with col4:
        st.metric("Users", f"{ratings['userId'].nunique():,}" if not ratings.empty else "0")

    st.subheader("How it works")
    st.write("1. Pick the mood you are in.")
    st.write("2. Like or pass movies in the Discover deck.")
    st.write("3. Save the winners and export your watchlist.")
    st.button("Start discovering", on_click=go_to, args=("Discover",))

elif page == "Discover":
    st.title("Discover")

    if st.session_state.fresh_batch:
        st.success("Fresh batch loaded — new random picks you haven't been shown yet.")
        st.session_state.fresh_batch = False

    moods = list(MOOD_GENRES.keys())
    st.radio(
        "How are you feeling?",
        moods,
        key="mood",
        horizontal=True,
        format_func=lambda mood: f"{MOOD_EMOJI[mood]} {mood}",
        on_change=reset_queue,
    )

    if not st.session_state.queue:
        refresh_queue()

    if not st.session_state.queue:
        st.warning("No unseen movies left for this mood. Start over to replay the deck.")
        if st.button("Start over"):
            st.session_state.disliked = []
            st.session_state.seen = []
            st.session_state.queue = []
            st.rerun()
    else:
        current_id = st.session_state.queue[0]
        movie = movie_by_id(current_id)
        if movie is None:
            st.session_state.queue.pop(0)
            st.rerun()

        movie_card(movie)

        like_col, pass_col, refresh_col = st.columns([1, 1, 2])
        with like_col:
            if st.button("👍 Like", width="stretch"):
                if current_id not in st.session_state.liked:
                    st.session_state.liked.append(current_id)
                add_to_watchlist(current_id)
                st.session_state.queue.pop(0)
                st.rerun()
        with pass_col:
            if st.button("👎 Pass", width="stretch"):
                if current_id not in st.session_state.disliked:
                    st.session_state.disliked.append(current_id)
                st.session_state.queue.pop(0)
                st.rerun()
        with refresh_col:
            if st.button("🔁 New recommendations", width="stretch"):
                refresh_queue()
                st.session_state.fresh_batch = True
                st.rerun()

        st.caption(
            f"{len(st.session_state.queue)} movies left in this batch · "
            f"{len(st.session_state.seen)} dealt this session · "
            f"{len(st.session_state.liked)} liked"
        )

elif page == "Search":
    st.title("Search the catalog")
    st.caption(
        "Search ignores upper and lower case. Every match is shown as a poster — "
        "use the page buttons to browse long result lists."
    )

    query = st.text_input("Search by title", placeholder="e.g. toy story")
    all_genres = sorted(
        {
            genre
            for value in catalog["genres"].fillna("")
            for genre in value.split("|")
            if genre
        }
    )
    selected_genres = st.multiselect("Filter by genre", all_genres)

    results = catalog.copy()
    if query.strip():
        results = results[
            results["title"].str.contains(
                query.strip(), case=False, regex=False, na=False
            )
        ]
    if selected_genres:
        results = results[
            results["genres"].fillna("").apply(
                lambda value: any(
                    genre in value.split("|") for genre in selected_genres
                )
            )
        ]

    st.write(f"{len(results):,} movies found")

    if results.empty:
        st.info(
            "No movies matched. Try a shorter title, check the spelling, "
            "or clear the genre filter."
        )
    else:
        page_size = 24
        total_pages = max((len(results) + page_size - 1) // page_size, 1)
        search_key = (
            f"{query.strip().lower()}|{','.join(sorted(selected_genres))}"
        )
        if st.session_state.search_key != search_key:
            st.session_state.search_key = search_key
            st.session_state.search_page = 1

        page_number = min(max(st.session_state.search_page, 1), total_pages)
        st.session_state.search_page = page_number
        start = (page_number - 1) * page_size
        page_results = results.iloc[start : start + page_size]

        st.caption("Click any movie poster to see its full details.")
        poster_grid(
            page_results,
            on_select=show_movie_details,
            key_prefix="search",
        )

        prev_col, info_col, next_col = st.columns([1, 3, 1])
        with prev_col:
            if st.button(
                "← Previous", disabled=page_number <= 1, width="stretch"
            ):
                st.session_state.search_page = page_number - 1
                st.rerun()
        with info_col:
            st.caption(
                f"Page {page_number} of {total_pages} · showing "
                f"{start + 1}–{min(start + page_size, len(results))} of "
                f"{len(results):,} matches"
            )
        with next_col:
            if st.button(
                "Next →", disabled=page_number >= total_pages, width="stretch"
            ):
                st.session_state.search_page = page_number + 1
                st.rerun()

elif page == "Watchlist":
    st.title("Your watchlist")

    if not st.session_state.watchlist:
        st.info("Your watchlist is empty. Like movies in Discover or add one from Search.")
    else:
        watchlist = catalog[
            catalog["movieId"].isin(st.session_state.watchlist)
        ].copy()
        st.dataframe(
            watchlist[["title", "genres", "year", "avg_rating", "rating_count"]],
            width="stretch",
            hide_index=True,
        )
        st.download_button(
            "Download watchlist CSV",
            watchlist.to_csv(index=False).encode("utf-8"),
            "moodflix_watchlist.csv",
            "text/csv",
        )

        remove_titles = st.multiselect("Remove movies", watchlist["title"].tolist())
        if st.button("Remove selected") and remove_titles:
            remove_ids = watchlist[
                watchlist["title"].isin(remove_titles)
            ]["movieId"].tolist()
            st.session_state.watchlist = [
                movie_id
                for movie_id in st.session_state.watchlist
                if movie_id not in remove_ids
            ]
            st.rerun()

elif page == "Insights":
    st.title("Model insights")

    genre_counts = (
        catalog["genres"]
        .fillna("")
        .str.get_dummies(sep="|")
        .sum()
        .drop(labels=["(no genres listed)"], errors="ignore")
        .sort_values(ascending=False)
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Movies", f"{len(catalog):,}")
    with col2:
        st.metric("Ratings", f"{len(ratings):,}")
    with col3:
        st.metric("Genres", len(genre_counts))
    with col4:
        st.metric("Users", f"{ratings['userId'].nunique():,}" if not ratings.empty else "0")

    st.subheader("Genre distribution")
    st.bar_chart(genre_counts.head(15))

    if not ratings.empty:
        st.subheader("Rating distribution")
        st.bar_chart(ratings["rating"].value_counts().sort_index())

    st.subheader("Top rated movies (minimum 50 ratings)")
    top_rated = catalog[catalog["rating_count"] >= 50].sort_values(
        ["avg_rating", "rating_count"], ascending=False
    )
    st.dataframe(
        top_rated[["title", "genres", "avg_rating", "rating_count"]].head(10),
        width="stretch",
        hide_index=True,
    )

    st.subheader("How the score is built")
    st.write(
        "45% content similarity · 20% rating quality · 10% popularity · "
        "15% collaborative signal · 10% mood match"
    )

elif page == "About":
    st.title("About MoodFlix")
    st.write(
        "MoodFlix is a mood-first movie recommender built with Streamlit, "
        "Pandas, and NumPy for the Web App Development for Data Science project."
    )

    st.subheader("Team")
    for member in TEAM:
        st.write(f"- {member}")

    st.subheader("Data")
    st.write(
        "MovieLens Latest Small dataset from GroupLens Research. "
        "Ratings are used to compute movie quality and collaborative signals."
    )
    st.caption(
        "Poster images courtesy of TMDB. This product uses the TMDB API "
        "but is not endorsed or certified by TMDB."
    )

    st.subheader("Ethics")
    st.info(
        "Recommendations are suggestions, not judgments. The app does not collect "
        "personal data; likes and watchlists live only in your current session."
    )
