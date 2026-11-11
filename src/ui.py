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
                radial-gradient(1200px 700px at 12% -15%, rgba(229,9,20,.20), transparent 60%),
                radial-gradient(900px 600px at 100% 0%, rgba(229,9,20,.10), transparent 55%),
                #0b0b0b;
            color: #f5f5f5;
            font-family: "Inter", "Helvetica Neue", Arial, sans-serif;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #000000, #0b0b0b);
            border-right: 1px solid rgba(229,9,20,.35);
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label {
            color: #e5e5e5;
        }

        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li {
            font-size: 16px;
            line-height: 1.65;
            color: #d2d2d2;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] p {
            font-size: 15px;
            font-weight: 500;
        }

        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
            color: #8c8c8c;
            font-size: 13px;
        }

        h1 {
            font-weight: 900 !important;
            letter-spacing: -0.02em;
            color: #ffffff !important;
            text-shadow: 0 0 44px rgba(229,9,20,.38);
        }

        h2, h3 {
            color: #f5f5f5 !important;
        }

        a {
            color: #e50914 !important;
        }

        .mf-card {
            background: linear-gradient(160deg, #1c1c1c, #141414);
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 16px;
            padding: 34px;
            margin: 8px 0 22px;
            box-shadow: 0 30px 70px rgba(0,0,0,.6);
            transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
        }

        .mf-card:hover {
            transform: translateY(-2px);
            border-color: rgba(229,9,20,.45);
            box-shadow: 0 34px 80px rgba(229,9,20,.16);
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
            border: 1px solid rgba(255,255,255,.12);
            box-shadow: 0 18px 40px rgba(0,0,0,.6);
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
            color: #e50914;
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
        }

        .mf-meta {
            color: #b3b3b3;
            font-size: 1rem;
            font-weight: 500;
            margin-bottom: 14px;
        }

        .mf-rating {
            color: #f5c518;
            font-size: 1.15rem;
            font-weight: 800;
        }

        .mf-rating span {
            color: #a3a3a3;
            font-size: .95rem;
            font-weight: 400;
        }

        .mf-tags {
            margin-top: 14px;
            color: #9c9c9c;
            font-size: .95rem;
            font-style: italic;
            line-height: 1.5;
        }

        div.stButton > button {
            background: #e50914;
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
            background: #f6121d;
            color: #ffffff;
            transform: translateY(-1px);
            box-shadow: 0 14px 30px rgba(229,9,20,.35);
        }

        div.stButton > button:active {
            transform: translateY(0);
        }

        [data-testid="stMetric"] {
            background: linear-gradient(160deg, #1c1c1c, #151515);
            border: 1px solid rgba(255,255,255,.08);
            border-left: 3px solid #e50914;
            border-radius: 12px;
            padding: 16px 18px;
        }

        [data-testid="stMetricLabel"] p {
            color: #b3b3b3 !important;
            font-size: 14px;
            font-weight: 600;
        }

        [data-testid="stMetricValue"] p {
            color: #ffffff !important;
            font-size: 34px;
            font-weight: 800;
        }

        [data-testid="stWidgetLabel"] p {
            color: #e5e5e5 !important;
            font-weight: 600;
        }

        [data-testid="stCaptionContainer"] p {
            color: #8c8c8c !important;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid rgba(255,255,255,.08);
            border-radius: 12px;
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
