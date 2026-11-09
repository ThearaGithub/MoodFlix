from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@st.cache_data(show_spinner=False)
def load_movies():
    movies = pd.read_csv(DATA_DIR / "movies.csv")
    movies["year"] = pd.to_numeric(
        movies["title"].str.extract(r"\((\d{4})\)\s*$")[0],
        errors="coerce",
    ).astype("Int64")
    movies["genre_list"] = movies["genres"].fillna("").str.split("|")

    tags_path = DATA_DIR / "tags.csv"
    if tags_path.exists():
        tags = pd.read_csv(tags_path)
        top_tags = (
            tags.groupby("movieId")["tag"]
            .apply(lambda values: ", ".join(values.value_counts().head(5).index))
            .rename("top_tags")
        )
        movies = movies.merge(top_tags, on="movieId", how="left")
    else:
        movies["top_tags"] = ""

    movies["top_tags"] = movies["top_tags"].fillna("")
    return movies


@st.cache_data(show_spinner=False)
def load_ratings():
    path = DATA_DIR / "ratings.csv"
    if not path.exists():
        return pd.DataFrame(columns=["userId", "movieId", "rating", "timestamp"])
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_movie_stats():
    ratings = load_ratings()
    if ratings.empty:
        return pd.DataFrame(columns=["movieId", "avg_rating", "rating_count"])
    return (
        ratings.groupby("movieId")["rating"]
        .agg(avg_rating="mean", rating_count="count")
        .reset_index()
    )


@st.cache_data(show_spinner=False)
def load_catalog():
    movies = load_movies()
    stats = load_movie_stats()
    catalog = movies.merge(stats, on="movieId", how="left")
    catalog["avg_rating"] = catalog["avg_rating"].fillna(0.0)
    catalog["rating_count"] = catalog["rating_count"].fillna(0).astype(int)
    return catalog
