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

        .stApp {
            background:
                radial-gradient(1200px 720px at 12% -15%, rgba(229,9,20,.42), transparent 62%),
                radial-gradient(950px 620px at 100% 0%, rgba(229,9,20,.28), transparent 58%),
                linear-gradient(180deg, #140305 0%, #0d0203 45%, #080101 100%);
            color: #f5f5f5;
            font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
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

        /* Invisible click layer: the whole poster acts as a button */
        [class*="st-key-mfposter_"] {
            position: relative;
        }

        [class*="st-key-mfposter_"] div.stButton {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            aspect-ratio: 2 / 3;
            margin: 0;
            z-index: 6;
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
