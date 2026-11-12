import re
from html import escape

import pandas as pd
import streamlit as st


def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800;900&display=swap');

        html, body, .stApp, [data-testid="stSidebar"], button, input, textarea, select {
            font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
        }

        /* Two red glows drift across the page. The layers use fixed
           attachment so background-position is measured against the
           viewport: percentage positions on the multi-thousand-pixel page
           body barely move the gradient at all. */
        .stApp {
            background:
                radial-gradient(540px 540px at 50% 50%, rgba(255,45,58,.5), rgba(255,45,58,0) 72%)
                    no-repeat fixed 0px 0px / 980px 980px,
                radial-gradient(460px 460px at 50% 50%, rgba(229,9,20,.42), rgba(229,9,20,0) 72%)
                    no-repeat fixed calc(100% - 120px) 40px / 860px 860px,
                radial-gradient(1100px 620px at 8% -10%, rgba(229,9,20,.34), transparent 64%)
                    no-repeat fixed 0px 0px / 100% 100%,
                linear-gradient(180deg, #170406 0%, #0d0203 45%, #080101 100%) fixed;
            animation: mf-drift 24s ease-in-out infinite alternate;
            color: #f5f5f5;
            font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
        }

        @keyframes mf-drift {
            0% {
                background-position: 0px 0px, calc(100% - 120px) 40px, 0 0, 0 0;
            }
            50% {
                background-position: 260px 200px, calc(100% - 470px) 280px, 0 0, 0 0;
            }
            100% {
                background-position: 120px 460px, calc(100% - 700px) 120px, 0 0, 0 0;
            }
        }

        @media (prefers-reduced-motion: reduce) {
            .stApp {
                animation: none;
            }
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a0406, #0d0203 55%, #070101);
            border-right: 1px solid rgba(229,9,20,.6);
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label {
            color: #f2d9da;
        }

        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li {
            font-size: 16px;
            line-height: 1.65;
            color: #e3cdcf;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] p {
            font-size: 15px;
            font-weight: 500;
        }

        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
            color: #b98d90;
            font-size: 13px;
        }

        [data-testid="stSidebar"] [data-testid="stImage"] img {
            border-radius: 18px;
            box-shadow: 0 12px 34px rgba(229,9,20,.4);
        }

        h1 {
            font-weight: 900 !important;
            letter-spacing: -0.02em;
            color: #ffffff !important;
            text-shadow: 0 0 48px rgba(229,9,20,.55);
        }

        [data-testid="stMain"] h1 {
            background: linear-gradient(90deg, #ff5c66, #e50914 55%, #ff2d3a);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent !important;
            text-shadow: none;
        }

        [data-testid="stSidebar"] h1 {
            background: none;
            -webkit-background-clip: border-box;
            background-clip: border-box;
            color: #ffffff !important;
            text-shadow: 0 0 30px rgba(229,9,20,.9);
        }

        h2, h3 {
            color: #ffe9ea !important;
        }

        a {
            color: #ff2d3a !important;
        }

        .mf-card {
            background: linear-gradient(160deg, rgba(229,9,20,.16), #19090b 50%, #120405);
            border: 1px solid rgba(229,9,20,.38);
            border-radius: 16px;
            padding: 34px;
            margin: 8px 0 22px;
            box-shadow: 0 30px 70px rgba(0,0,0,.6);
            transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
        }

        .mf-card:hover {
            transform: translateY(-2px);
            border-color: rgba(229,9,20,.8);
            box-shadow: 0 34px 90px rgba(229,9,20,.35);
        }

        .mf-card-with-poster {
            display: flex;
            gap: 26px;
            align-items: flex-start;
        }

        .mf-poster {
            width: 160px;
            min-width: 160px;
            border-radius: 8px;
            border: 1px solid rgba(229,9,20,.35);
            box-shadow: 0 18px 44px rgba(229,9,20,.25);
            display: block;
        }

        .mf-body {
            flex: 1;
            min-width: 0;
        }

        @media (max-width: 700px) {
            .mf-card-with-poster {
                flex-direction: column;
            }

            .mf-poster {
                width: 100%;
                max-width: 220px;
                min-width: 0;
            }
        }

        .mf-kicker {
            color: #ff2d3a;
            font-size: .78rem;
            font-weight: 800;
            letter-spacing: .22em;
            text-transform: uppercase;
        }

        .mf-title {
            font-size: 2.3rem;
            font-weight: 900;
            line-height: 1.1;
            margin: 10px 0 8px;
            color: #ffffff;
            text-shadow: 0 0 30px rgba(229,9,20,.35);
        }

        .mf-meta {
            color: #d8b4b7;
            font-size: 1rem;
            font-weight: 500;
            margin-bottom: 14px;
        }

        .mf-rating {
            color: #ff6b74;
            font-size: 1.15rem;
            font-weight: 800;
        }

        .mf-rating span {
            color: #c39a9d;
            font-size: .95rem;
            font-weight: 400;
        }

        .mf-tags {
            margin-top: 14px;
            color: #c49fa2;
            font-size: .95rem;
            font-style: italic;
            line-height: 1.5;
        }

        div.stButton > button {
            background: linear-gradient(100deg, #f6121d, #e50914 55%, #b20710);
            color: #ffffff;
            font-size: 1rem;
            font-weight: 800;
            letter-spacing: .02em;
            border: none;
            border-radius: 6px;
            padding: 10px 20px;
            transition: background .15s ease, transform .15s ease, box-shadow .15s ease;
        }

        div.stButton > button:hover {
            background: linear-gradient(100deg, #ff2d3a, #f6121d 55%, #c00a12);
            color: #ffffff;
            transform: translateY(-1px);
            box-shadow: 0 14px 30px rgba(229,9,20,.45);
        }

        div.stButton > button:active {
            transform: translateY(0);
        }

        [data-testid="stMetric"] {
            background: linear-gradient(160deg, rgba(229,9,20,.14), #170709);
            border: 1px solid rgba(229,9,20,.28);
            border-left: 4px solid #e50914;
            border-radius: 12px;
            padding: 16px 18px;
        }

        [data-testid="stMetricLabel"] p {
            color: #d0a7aa !important;
            font-size: 14px;
            font-weight: 600;
        }

        [data-testid="stMetricValue"] p {
            color: #ff4d57 !important;
            font-size: 34px;
            font-weight: 800;
        }

        [data-testid="stWidgetLabel"] p {
            color: #f2d9da !important;
            font-weight: 600;
        }

        [data-testid="stCaptionContainer"] p {
            color: #b98d90 !important;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid rgba(229,9,20,.25);
            border-radius: 12px;
        }

        ::selection {
            background: #e50914;
            color: #ffffff;
        }

        [role="radiogroup"] label:has(input:checked) p {
            color: #ff4d57 !important;
            font-weight: 700;
        }

        .mf-tile {
            background: linear-gradient(160deg, rgba(229,9,20,.10), #170709);
            border: 1px solid rgba(229,9,20,.25);
            border-radius: 12px;
            overflow: hidden;
            margin-bottom: 18px;
            transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease;
        }

        .mf-tile:hover,
        [class*="st-key-mfposter_"]:hover .mf-tile {
            transform: translateY(-3px);
            border-color: rgba(229,9,20,.75);
            box-shadow: 0 20px 44px rgba(229,9,20,.28);
        }

        .mf-tile-img {
            width: 100%;
            aspect-ratio: 2 / 3;
            object-fit: cover;
            display: block;
            background: #1a0a0c;
        }

        .mf-tile-noimg {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 18px;
            text-align: center;
            color: #ff8a8f;
            font-weight: 700;
            font-size: .95rem;
        }

        .mf-tile-body {
            padding: 10px 12px 12px;
        }

        .mf-tile-title {
            color: #ffffff;
            font-weight: 700;
            font-size: .95rem;
            line-height: 1.25;
            min-height: 2.4em;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        .mf-tile-meta {
            color: #c49fa2;
            font-size: .8rem;
            margin-top: 4px;
        }

        .mf-meter {
            background: linear-gradient(160deg, rgba(229,9,20,.12), #170709);
            border: 1px solid rgba(229,9,20,.28);
            border-radius: 12px;
            padding: 14px 18px 16px;
            margin: 6px 0 14px;
        }

        .mf-meter-head {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            gap: 12px;
            color: #f2d9da;
            font-size: .85rem;
            font-weight: 700;
            letter-spacing: .04em;
            text-transform: uppercase;
        }

        .mf-meter-head strong {
            color: #ff4d57;
            font-size: 1.5rem;
            letter-spacing: 0;
        }

        .mf-meter-track {
            margin-top: 10px;
            height: 10px;
            border-radius: 999px;
            background: rgba(255,255,255,.08);
            overflow: hidden;
        }

        .mf-meter-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #7a0510, #e50914 60%, #ff5c66);
            box-shadow: 0 0 18px rgba(229,9,20,.6);
            transition: width .4s ease;
        }

        .mf-overview {
            color: #dcc4c6;
            font-size: 1rem;
            line-height: 1.7;
            margin: 2px 0 16px;
        }

        .mf-cast-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(118px, 1fr));
            gap: 14px;
            margin: 6px 0 18px;
        }

        .mf-cast-card {
            background: linear-gradient(160deg, rgba(229,9,20,.12), #170709);
            border: 1px solid rgba(229,9,20,.28);
            border-radius: 12px;
            padding: 14px 10px 12px;
            text-align: center;
        }

        .mf-cast-photo {
            width: 84px;
            height: 84px;
            border-radius: 50%;
            object-fit: cover;
            display: block;
            margin: 0 auto 9px;
            border: 2px solid rgba(229,9,20,.55);
            background: #2a0b0e;
            box-shadow: 0 10px 24px rgba(0,0,0,.5);
        }

        .mf-cast-initials {
            display: flex;
            align-items: center;
            justify-content: center;
            color: #ff8a8f;
            font-size: 1.35rem;
            font-weight: 800;
            letter-spacing: .04em;
        }

        .mf-cast-name {
            color: #ffffff;
            font-weight: 700;
            font-size: .88rem;
            line-height: 1.2;
        }

        .mf-cast-role {
            color: #c49fa2;
            font-size: .76rem;
            line-height: 1.3;
            margin-top: 3px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        /* Invisible click layer: the whole poster acts as a button */
        [class*="st-key-mfposter_"] {
            position: relative;
        }

        /* Streamlit gives each button its own position:relative wrapper,
           so the wrapper (not just div.stButton) must be overlaid. */
        [class*="st-key-mfposter_"] > div[data-testid="stElementContainer"]:has(> div.stButton) {
            position: absolute;
            top: 0;
            left: 0;
            width: 100% !important;
            aspect-ratio: 2 / 3;
            margin: 0;
            z-index: 6;
        }

        [class*="st-key-mfposter_"] div.stButton {
            width: 100%;
            height: 100%;
            margin: 0;
        }

        [class*="st-key-mfposter_"] div.stButton > button {
            width: 100%;
            height: 100%;
            padding: 0;
            border: none;
            border-radius: 12px;
            background: transparent;
            opacity: 0;
            cursor: pointer;
        }

        /* Invisible click layer across the full feature card on Discover */
        [class*="st-key-mfcard_"] {
            position: relative;
        }

        [class*="st-key-mfcard_"] > div[data-testid="stElementContainer"]:has(> div.stButton) {
            position: absolute;
            inset: 0;
            width: 100% !important;
            height: 100% !important;
            margin: 0;
            z-index: 6;
        }

        [class*="st-key-mfcard_"] div.stButton {
            width: 100%;
            height: 100%;
            margin: 0;
        }

        [class*="st-key-mfcard_"] div.stButton > button {
            width: 100%;
            height: 100%;
            padding: 0;
            border: none;
            border-radius: 16px;
            background: transparent;
            opacity: 0;
            cursor: pointer;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def movie_card(movie):
    title = escape(str(movie["title"]))
    genres = escape(str(movie["genres"]).replace("|", " · "))
    tags = escape(str(movie.get("top_tags", "")))
    rating = float(movie.get("avg_rating", 0.0))
    count = int(movie.get("rating_count", 0))
    year = movie.get("year")
    year_text = ""
    if year is not None and not pd.isna(year):
        year_text = f" · {int(year)}"

    poster_url = str(movie.get("poster_url", "") or "").strip()
    card_class = "mf-card"
    poster_html = ""
    if poster_url.startswith(("https://", "http://")):
        card_class += " mf-card-with-poster"
        poster_html = (
            f'<img class="mf-poster" src="{escape(poster_url, quote=True)}" '
            f'alt="{title} poster" loading="lazy">'
        )

    st.markdown(
        f"""
        <div class="{card_class}">
            {poster_html}
            <div class="mf-body">
                <div class="mf-kicker">Now showing{year_text}</div>
                <div class="mf-title">{title}</div>
                <div class="mf-meta">{genres}</div>
                <div class="mf-rating">⭐ {rating:.2f} <span>({count:,} ratings)</span></div>
                <div class="mf-tags">{tags}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def clickable_movie_card(movie, on_select, key_prefix="card"):
    """Render the feature card with an invisible details click layer."""
    movie_id = int(movie["movieId"])
    with st.container(key=f"mfcard_{key_prefix}_{movie_id}"):
        movie_card(movie)
        if st.button(
            "View details",
            key=f"{key_prefix}_card_open_{movie_id}",
        ):
            on_select(movie)


def overview_block(text):
    """Render the plot summary paragraph."""
    text = str(text or "").strip()
    if not text:
        st.caption("No description is available for this movie.")
        return
    st.markdown(
        f'<div class="mf-overview">{escape(text)}</div>',
        unsafe_allow_html=True,
    )


def taste_meter(value, label="Model taste match"):
    """Horizontal bar visualising a 0-1 model score."""
    percent = max(0, min(100, int(round(float(value) * 100))))
    st.markdown(
        f'<div class="mf-meter"><div class="mf-meter-head">'
        f"<span>{escape(str(label))}</span><strong>{percent}%</strong>"
        f'</div><div class="mf-meter-track">'
        f'<div class="mf-meter-fill" style="width:{percent}%"></div>'
        f"</div></div>",
        unsafe_allow_html=True,
    )


def trailer_block(trailer):
    if not trailer or not trailer.get("key"):
        st.caption("Trailer not available for this movie.")
        return

    key = str(trailer["key"]).strip()
    st.video(f"https://www.youtube.com/watch?v={key}")
    title = str(trailer.get("name", "") or "").strip()
    if title:
        st.caption(f"🎬 {title}")


def cast_grid(cast):
    if not cast:
        st.caption("Cast information is not available for this movie.")
        return

    cards = []
    for person in cast:
        name = str(person.get("name", "") or "").strip()
        if not name:
            continue
        role = str(person.get("character", "") or "").strip()
        photo_url = str(person.get("photo_url", "") or "").strip()
        safe_name = escape(name)
        safe_role = escape(role)

        if photo_url.startswith(("https://", "http://")):
            media = (
                f'<img class="mf-cast-photo" '
                f'src="{escape(photo_url, quote=True)}" '
                f'alt="{safe_name}" loading="lazy">'
            )
        else:
            parts = [part for part in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", name)]
            initials = "".join(part[0] for part in parts[:2]).upper() or "?"
            media = (
                f'<div class="mf-cast-photo mf-cast-initials">'
                f"{escape(initials)}</div>"
            )

        role_html = (
            f'<div class="mf-cast-role">{safe_role}</div>'
            if safe_role
            else ""
        )
        # Keep each card on a single line with no blank lines between
        # cards: Markdown ends an HTML block at a blank line and would
        # render the leftover indented markup as a code block.
        cards.append(
            f'<div class="mf-cast-card">{media}'
            f'<div class="mf-cast-name">{safe_name}</div>'
            f"{role_html}</div>"
        )

    if not cards:
        st.caption("Cast information is not available for this movie.")
        return

    st.markdown(
        f'<div class="mf-cast-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def _poster_tile(movie):
    title = escape(str(movie.get("title", "")))
    year = movie.get("year")
    rating = float(movie.get("avg_rating", 0.0) or 0.0)
    count = int(movie.get("rating_count", 0) or 0)
    poster_url = str(movie.get("poster_url", "") or "").strip()

    meta_parts = []
    if year is not None and not pd.isna(year):
        meta_parts.append(str(int(year)))
    meta_parts.append(f"⭐ {rating:.1f}")
    if count > 0:
        meta_parts.append(f"{count:,} ratings")
    meta = " · ".join(meta_parts)

    if poster_url.startswith(("https://", "http://")):
        media = (
            f'<img class="mf-tile-img" src="{escape(poster_url, quote=True)}" '
            f'alt="{title} poster" loading="lazy">'
        )
    else:
        media = f'<div class="mf-tile-img mf-tile-noimg"><span>{title}</span></div>'

    st.markdown(
        f"""
        <div class="mf-tile">
            {media}
            <div class="mf-tile-body">
                <div class="mf-tile-title">{title}</div>
                <div class="mf-tile-meta">{meta}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def poster_grid(movies, columns=6, on_select=None, key_prefix="tile"):
    records = movies.to_dict("records")
    for start in range(0, len(records), columns):
        row = records[start : start + columns]
        cols = st.columns(columns)
        for col, movie in zip(cols, row):
            movie_id = int(movie["movieId"])
            with col:
                with st.container(key=f"mfposter_{key_prefix}_{movie_id}"):
                    _poster_tile(movie)
                    if on_select is not None and st.button(
                        "View details",
                        key=f"{key_prefix}_open_{movie_id}",
                    ):
                        on_select(movie)
