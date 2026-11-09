import streamlit as st

from src.data_loader import load_catalog, load_ratings
from src.mood import MOOD_EMOJI, MOOD_GENRES
from src.recommender import recommend
from src.ui import inject_css, movie_card

st.set_page_config(page_title="MoodFlix", page_icon="🎬", layout="wide")
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
    recommendations = recommend(
        catalog,
        ratings,
        st.session_state.liked,
        st.session_state.disliked,
        mood=st.session_state.mood,
        n=20,
    )
    st.session_state.queue = recommendations["movieId"].tolist()


with st.sidebar:
    st.title("🎬 MoodFlix")
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

    moods = list(MOOD_GENRES.keys())
    current_mood = st.radio(
        "How are you feeling?",
        moods,
        index=moods.index(st.session_state.mood),
        horizontal=True,
        format_func=lambda mood: f"{MOOD_EMOJI[mood]} {mood}",
    )
    if current_mood != st.session_state.mood:
        st.session_state.mood = current_mood
        st.session_state.queue = []

    if not st.session_state.queue:
        refresh_queue()

    if not st.session_state.queue:
        st.warning("No movies left in this batch. Reset your passes to see more.")
        if st.button("Reset passes"):
            st.session_state.disliked = []
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
                st.rerun()

        st.caption(
            f"{len(st.session_state.queue)} movies left in this batch · "
            f"{len(st.session_state.liked)} liked"
        )

elif page == "Search":
    st.title("Search the catalog")

    query = st.text_input("Search by title", placeholder="e.g. Toy Story")
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
    if query:
        results = results[
            results["title"].str.contains(query, case=False, na=False)
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
    st.dataframe(
        results[["title", "genres", "year", "avg_rating", "rating_count"]].head(50),
        width="stretch",
        hide_index=True,
    )

    if not results.empty:
        options = results.head(50)
        selected_title = st.selectbox("Open a movie", options["title"].tolist())
        selected_movie = options[options["title"] == selected_title].iloc[0]
        movie_card(selected_movie)
        if st.button("Add to watchlist"):
            add_to_watchlist(int(selected_movie["movieId"]))
            st.success("Added to watchlist.")

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

    st.subheader("Ethics")
    st.info(
        "Recommendations are suggestions, not judgments. The app does not collect "
        "personal data; likes and watchlists live only in your current session."
    )
