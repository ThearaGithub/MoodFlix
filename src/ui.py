from html import escape

import pandas as pd
import streamlit as st


def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

        html, body, .stApp, [data-testid="stSidebar"], button, input, textarea, select {
            font-family: "Outfit", "Segoe UI", system-ui, sans-serif;
        }

        .stApp {
            background:
                radial-gradient(1100px 620px at 8% -10%, rgba(124,92,255,.28), transparent 60%),
                radial-gradient(900px 560px at 100% 0%, rgba(34,211,238,.18), transparent 55%),
                #070b12;
            color: #eef4ff;
            font-family: "Outfit", "Segoe UI", system-ui, sans-serif;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b1220, #070b12);
            border-right: 1px solid rgba(255,255,255,.08);
        }

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label {
            color: #dbe7ff;
        }

        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li {
            font-size: 16px;
            line-height: 1.6;
        }

        [data-testid="stSidebar"] [data-testid="stRadio"] p {
            font-size: 15px;
            font-weight: 500;
        }

        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
            color: #9fb2cf;
            font-size: 13px;
        }

        h1 {
            font-weight: 800 !important;
            letter-spacing: -0.03em;
            background: linear-gradient(90deg, #c4b5fd, #67e8f9);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent !important;
        }

        .mf-card {
            background: linear-gradient(160deg, rgba(255,255,255,.09), rgba(255,255,255,.02));
            border: 1px solid rgba(255,255,255,.12);
            border-radius: 24px;
            padding: 34px;
            margin: 8px 0 22px;
            box-shadow: 0 30px 70px rgba(0,0,0,.45);
        }

        .mf-kicker {
            color: #67e8f9;
            font-size: .78rem;
            font-weight: 700;
            letter-spacing: .2em;
            text-transform: uppercase;
        }

        .mf-title {
            font-size: 2.3rem;
            font-weight: 800;
            line-height: 1.1;
            margin: 10px 0 8px;
            color: #f8fbff;
        }

        .mf-meta {
            color: #c3d2ea;
            font-size: 1rem;
            font-weight: 500;
            margin-bottom: 14px;
        }

        .mf-rating {
            color: #ffd166;
            font-size: 1.15rem;
            font-weight: 700;
        }

        .mf-rating span {
            color: #a9b8d0;
            font-size: .95rem;
            font-weight: 400;
        }

        .mf-tags {
            margin-top: 14px;
            color: #b9c9e5;
            font-size: .95rem;
            font-style: italic;
            line-height: 1.5;
        }

        div.stButton > button {
            background-image: linear-gradient(100deg, #7c5cff, #22d3ee);
            color: #04121f;
            font-size: 1rem;
            font-weight: 700;
            border: none;
            border-radius: 12px;
            padding: 10px 20px;
        }

        div.stButton > button:hover {
            filter: brightness(1.08);
            box-shadow: 0 14px 30px rgba(34,211,238,.3);
        }

        [data-testid="stMetric"] {
            background: rgba(255,255,255,.045);
            border: 1px solid rgba(255,255,255,.09);
            border-radius: 16px;
            padding: 16px 18px;
        }

        [data-testid="stMetricLabel"] p {
            color: #b9c9e5 !important;
            font-size: 14px;
            font-weight: 600;
        }

        [data-testid="stMetricValue"] p {
            color: #f4f8ff !important;
            font-size: 34px;
            font-weight: 700;
        }

        [data-testid="stWidgetLabel"] p {
            color: #e6efff !important;
            font-weight: 600;
        }

        [data-testid="stCaptionContainer"] p {
            color: #aebdd6 !important;
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

    st.markdown(
        f"""
        <div class="mf-card">
            <div class="mf-kicker">Now showing{year_text}</div>
            <div class="mf-title">{title}</div>
            <div class="mf-meta">{genres}</div>
            <div class="mf-rating">⭐ {rating:.2f} <span>({count:,} ratings)</span></div>
            <div class="mf-tags">{tags}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
