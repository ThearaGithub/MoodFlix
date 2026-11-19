import threading
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from src.data_loader import load_catalog, load_ratings
from src.extras import (
    movie_info_future,
    prefetch_movie_info,
    request_trailer,
)
from src.model import (
    get_model,
    model_metrics,
    ranking_scores,
    similarity_scores,
    taste_match,
    taste_scores,
)
from src import vision
from src.mood import MOOD_EMOJI, MOOD_GENRES
from src.recommender import recommend
from src.ui import (
    cast_grid,
    clickable_movie_card,
    inject_css,
    movie_card,
    overview_block,
    poster_grid,
    scroll_dialog_to_top,
    taste_meter,
    trailer_block,
    watch_providers_block,
)

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
if "details_movie_id" not in st.session_state:
    st.session_state.details_movie_id = None
if "prefetched_movies" not in st.session_state:
    st.session_state.prefetched_movies = set()


try:
    catalog = load_catalog()
    ratings = load_ratings()
except FileNotFoundError:
    st.error(
        "Movie data was not found. Run `python scripts/download_data.py` "
        "and then refresh this page."
    )
    st.stop()


@st.cache_resource
def warm_model():
    """Train the latent model in the background at startup.

    The first details dialog otherwise pays the ~2.5 s training time while
    the user waits for the "You may like" grid.
    """
    threading.Thread(
        target=get_model, name="mf-model", daemon=True
    ).start()
    return True


warm_model()


def movie_by_id(movie_id):
    match = catalog[catalog["movieId"] == movie_id]
    return match.iloc[0] if not match.empty else None


def movie_extras_args(movie):
    """The ``(tmdbId, imdbId, title, year)`` tuple used for extras lookups."""
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
    return tmdb_value, imdb_value, str(movie.get("title", "")), year_value


def prefetch_picks(picks):
    """Warm the plot/cast cache for posters the user is likely to open."""
    for _, movie in picks.iterrows():
        movie_id = int(movie["movieId"])
        if movie_id in st.session_state.prefetched_movies:
            continue
        st.session_state.prefetched_movies.add(movie_id)
        prefetch_movie_info(*movie_extras_args(movie))


def model_bar_chart(values, axis_title, zero, highlight):
    """Themed bar chart for the model metrics on the Insights page."""
    frame = pd.DataFrame(
        {
            "label": list(values.keys()),
            "value": list(values.values()),
        }
    )
    frame["is_highlight"] = frame["label"] == highlight
    base = alt.Chart(frame).encode(
        x=alt.X("label:N", title=None, sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y(
            "value:Q",
            title=axis_title,
            scale=alt.Scale(zero=zero),
            axis=alt.Axis(format=".3f"),
        ),
    )
    bars = base.mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        color=alt.condition(
            alt.datum.is_highlight,
            alt.value("#e50914"),
            alt.value("#6b1116"),
        ),
        tooltip=[
            alt.Tooltip("label:N", title="Ranker"),
            alt.Tooltip("value:Q", title=axis_title, format=".4f"),
        ],
    )
    labels = base.mark_text(dy=-8, color="#f5f5f5", fontSize=11).encode(
        text=alt.Text("value:Q", format=".3f")
    )
    return (bars + labels).properties(height=260)


def model_scatter_chart(actual, predicted, limit=2000):
    """Held-out ratings against the model's guesses, with a perfect-fit line."""
    frame = pd.DataFrame({"actual": actual, "predicted": predicted})
    if len(frame) > limit:
        frame = frame.sample(limit, random_state=0)
    diagonal = pd.DataFrame({"actual": [0.5, 5.0], "predicted": [0.5, 5.0]})
    points = (
        alt.Chart(frame)
        .mark_circle(size=8, opacity=0.35, color="#e50914")
        .encode(
            x=alt.X(
                "actual:Q",
                title="Actual rating",
                scale=alt.Scale(domain=[0.5, 5]),
                axis=alt.Axis(values=[1, 2, 3, 4, 5]),
            ),
            y=alt.Y(
                "predicted:Q",
                title="Predicted rating",
                scale=alt.Scale(domain=[0.5, 5]),
            ),
            tooltip=[
                alt.Tooltip("actual:Q", title="Actual", format=".1f"),
                alt.Tooltip("predicted:Q", title="Predicted", format=".2f"),
            ],
        )
    )
    perfect = (
        alt.Chart(diagonal)
        .mark_line(color="#f5f5f5", strokeDash=[4, 4])
        .encode(x="actual:Q", y="predicted:Q")
    )
    return (points + perfect).properties(height=320)


def may_like_picks(n=6, seed_movie_id=None):
    """Movies ranked for the session user, excluding what is already handled.

    With likes the score is personal (taste + quality); without them it falls
    back to the latent similarity to ``seed_movie_id``.
    """
    scores = (
        ranking_scores(catalog, st.session_state.liked)
        if st.session_state.liked
        else similarity_scores(catalog, seed_movie_id)
        if seed_movie_id is not None
        else None
    )
    if scores is None:
        return None

    skip = set(st.session_state.liked) | set(st.session_state.disliked)
    if seed_movie_id is not None:
        skip.add(int(seed_movie_id))
    return (
        catalog.assign(match=scores)
        .loc[lambda frame: ~frame["movieId"].isin(skip)]
        .nlargest(n, "match")
    )


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
        personal_scores=taste_scores(catalog, st.session_state.liked),
    )
    st.session_state.queue = recommendations["movieId"].tolist()


def reset_queue():
    st.session_state.queue = []


def set_mood(mood):
    """Apply a mood picked outside the radio (e.g. the camera detector)."""
    st.session_state.mood = mood
    st.session_state.queue = []


def close_movie_details():
    """Forget the selected movie so a dismissed dialog stays closed."""
    st.session_state.details_movie_id = None


@st.fragment(run_every=1.0)
def wait_for_trailer(title, year):
    """Poll the background trailer search; rerun when it has an answer.

    The trailer lookup is the slowest part of the details dialog (YouTube
    regularly takes several seconds), so it runs in a daemon thread. This
    one-second poll keeps the dialog responsive, and its app rerun swaps the
    placeholder for the video once the search finishes.
    """
    _, ready = request_trailer(title, year)
    if ready:
        st.rerun()
    st.caption("Searching YouTube… this usually takes a few seconds.")


@st.dialog("Movie details", width="large", on_dismiss=close_movie_details)
def show_movie_details():
    # The movie comes from session state instead of an argument because a
    # dialog cannot open another dialog: clicking a poster inside this one
    # stores a new id and the dialog's fragment rerun renders that movie.
    movie = movie_by_id(st.session_state.details_movie_id)
    if movie is None:
        st.caption("This movie is no longer available.")
        return

    movie_card(movie)
    tmdb_value, imdb_value, title, year_value = movie_extras_args(movie)

    # Plot and cast only: the slow trailer search is started separately below.
    # The future is shared with the picks grid, so a prefetched movie opens
    # without repeating the same Wikipedia requests.
    with st.spinner("Loading plot and cast…"):
        info = movie_info_future(
            tmdb_value, imdb_value, title, year_value
        ).result()

    overview_block(info.get("overview"))

    match = taste_match(movie["movieId"], st.session_state.liked)
    if match is not None:
        taste_meter(
            match,
            f"Model taste match · {len(st.session_state.liked)} liked",
        )

    st.divider()
    st.subheader("Trailer")
    trailer = info.get("trailer")
    if trailer is None:
        trailer, trailer_ready = request_trailer(title, year_value)
        if trailer_ready:
            trailer_block(trailer)
        else:
            with st.container():
                wait_for_trailer(title, year_value)
    else:
        trailer_block(trailer)

    st.subheader("Cast")
    cast_grid(info.get("cast") or [])

    if info.get("source") == "TMDB":
        if info.get("trailer"):
            st.caption("Trailer and cast via TMDB.")
        else:
            st.caption("Cast via TMDB · Trailer via YouTube.")
    elif info.get("source") == "web":
        st.caption("Trailer via YouTube · Cast via Wikipedia/Wikidata.")

    st.subheader("Where to watch")
    watch_providers_block(info.get("watch"))

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

    picks = may_like_picks(n=4, seed_movie_id=movie_id)
    if picks is not None and not picks.empty:
        st.divider()
        st.subheader("You may like")
        st.caption(
            "Chosen by the recommendation model"
            + (
                " from your taste profile."
                if st.session_state.liked
                else " as movies with a similar latent signature."
            )
        )
        poster_grid(
            picks,
            columns=4,
            on_select=open_movie_details,
            key_prefix=f"dialog_{movie_id}",
        )
        prefetch_picks(picks)

    # Also adds the floating "↑ Top" button for long dialogs.
    scroll_dialog_to_top(movie_id)


def open_movie_details(movie):
    """Show the details dialog for a clicked poster.

    Only the id is stored here; the dialog itself is opened at the bottom
    of this script. A dialog created inside a widget callback is closed
    again by the rerun that follows the callback.
    """
    st.session_state.details_movie_id = int(movie["movieId"])


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

    st.divider()
    st.subheader("You may like")
    if not st.session_state.liked:
        st.caption(
            "Like a few movies in Discover and the recommendation model will "
            "fill this row with movies that match your taste."
        )
    else:
        picks = may_like_picks(n=6)
        if picks is None or picks.empty:
            st.caption("The recommendation model is not available right now.")
        else:
            st.caption(
                "Picked by the recommendation model from the "
                f"{len(st.session_state.liked)} movie"
                f"{'s' if len(st.session_state.liked) != 1 else ''} you liked. "
                "Click a poster for details."
            )
            poster_grid(
                picks,
                on_select=open_movie_details,
                key_prefix="maylike",
            )
            prefetch_picks(picks)

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

    with st.expander("📷 Detect my mood from a photo", expanded=True):
        st.caption(
            "The browser asks for camera access when this page opens, but "
            "nothing is captured or analysed until you press Take Photo. The "
            "photo is read on this machine to guess your expression, then "
            "deleted — never stored or uploaded. The mood buttons above "
            "always win."
        )
        if not vision.is_available():
            st.info(vision.INSTALL_HINT)
        else:
            photo = st.camera_input("Look at the camera", key="mood_photo")
            if photo is not None:
                with st.spinner("Reading your expression…"):
                    try:
                        suggestion = vision.suggest_mood(photo.getvalue())
                    except vision.VisionUnavailable:
                        st.info(vision.INSTALL_HINT)
                        suggestion = None
                    except vision.VisionError as exc:
                        st.warning(str(exc))
                        suggestion = None

                if suggestion:
                    taste_meter(
                        suggestion["confidence"],
                        f"{suggestion['emoji']} Looks {suggestion['emotion']}",
                    )
                    st.write(
                        f"Suggested mood: {MOOD_EMOJI[suggestion['mood']]} "
                        f"**{suggestion['mood']}**"
                    )
                    runner_up = suggestion.get("runner_up")
                    if runner_up:
                        st.caption(
                            "Second guess: "
                            f"{MOOD_EMOJI[runner_up['mood']]} "
                            f"{runner_up['mood']} "
                            f"({runner_up['confidence'] * 100:.0f}%)"
                        )
                    st.button(
                        f"Use {suggestion['mood']}",
                        key="use_camera_mood",
                        on_click=set_mood,
                        args=(suggestion["mood"],),
                    )
                    st.caption(
                        f"Expressions map onto {len(vision.CAMERA_MOODS)} of the "
                        f"{len(MOOD_GENRES)} moods. "
                        f"{' and '.join(vision.MANUAL_ONLY_MOODS)} have no facial "
                        "signal — pick those above."
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

        clickable_movie_card(
            movie,
            on_select=open_movie_details,
            key_prefix="discover",
        )

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
            on_select=open_movie_details,
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
        "15% latent-factor personal match · 10% mood match"
    )

    st.subheader("Recommendation model")
    st.caption(
        "Biased matrix factorisation (truncated SVD, 20 latent factors) "
        "trained on MovieLens ratings with a per-user holdout of the "
        "latest 20% of ratings."
    )
    metrics = model_metrics()
    if not metrics:
        st.info("The recommendation model could not be trained on this dataset.")
    else:
        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric(
                "RMSE (model)",
                f"{metrics['rmse_model']:.3f}",
                delta=f"{metrics['rmse_model'] - metrics['rmse_baseline']:+.3f} vs mean",
                delta_color="inverse",
            )
        with metric_cols[1]:
            st.metric("MAE (model)", f"{metrics['mae_model']:.3f}")
        with metric_cols[2]:
            st.metric(
                f"Precision@{metrics['k']}",
                f"{metrics['precision_model']:.3f}",
                delta=f"{metrics['precision_model'] - metrics['precision_popularity']:+.3f} vs popularity",
            )

        st.subheader("Model performance")
        chart_cols = st.columns(2)
        with chart_cols[0]:
            st.caption("Rating error — lower is better")
            st.altair_chart(
                model_bar_chart(
                    {
                        "Global mean": metrics["rmse_baseline"],
                        "Movie + user biases": metrics["rmse_item_bias"],
                        "SVD model": metrics["rmse_model"],
                    },
                    "RMSE",
                    zero=False,
                    highlight="SVD model",
                ),
                use_container_width=True,
            )
        with chart_cols[1]:
            st.caption(
                f"Ranking quality — precision@{metrics['k']}, higher is better"
            )
            st.altair_chart(
                model_bar_chart(
                    {
                        "Popularity": metrics["precision_popularity"],
                        "Quality prior": metrics["precision_quality"],
                        "Model + quality": metrics["precision_model"],
                    },
                    f"Precision@{metrics['k']}",
                    zero=True,
                    highlight="Model + quality",
                ),
                use_container_width=True,
            )

        st.dataframe(
            pd.DataFrame(
                {
                    "Ranking baseline": [
                        "Popularity",
                        "Rating quality + popularity",
                        "Model (latent taste + quality)",
                    ],
                    f"Precision@{metrics['k']}": [
                        metrics["precision_popularity"],
                        metrics["precision_quality"],
                        metrics["precision_model"],
                    ],
                }
            ),
            width="stretch",
            hide_index=True,
        )

        holdout = get_model().get("holdout")
        if holdout is not None:
            st.subheader("Predicted vs actual")
            st.caption(
                "Each dot is one held-out rating; the dashed line is a perfect "
                "prediction. The tighter the cloud hugs the line, the better "
                "the model's star guess."
            )
            st.altair_chart(
                model_scatter_chart(holdout["actual"], holdout["predicted"]),
                use_container_width=True,
            )

        st.caption(
            f"Trained on {metrics['train_ratings']:,} ratings, tested on "
            f"{metrics['test_ratings']:,} held-out ratings · "
            f"{metrics['users']} users · {metrics['items']:,} movies · "
            f"{metrics['factors']} latent factors. Item-bias-only baseline "
            f"RMSE: {metrics['rmse_item_bias']:.3f}."
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
    st.caption(
        "Optional camera mood detection reads a single photo on this machine "
        "to guess an expression. Access is only requested on the Discover page "
        "and nothing is captured until you take a photo; the image is deleted "
        "immediately, never uploaded or saved. It is a guess, not a diagnosis, "
        "and the manual mood buttons always override it."
    )


# Opened during the normal script run, never inside a callback: a dialog
# created in a callback is closed again by the rerun that follows it.
if st.session_state.details_movie_id is not None:
    show_movie_details()
