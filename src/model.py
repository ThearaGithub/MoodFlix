"""Latent-factor recommendation model.

MoodFlix ranks movies with a fixed-weight blend. The collaborative part of
that blend used to be a hand-built heuristic; this module supplies a trained
model instead.

The model is a biased matrix factorisation trained with a truncated SVD:

    rating(u, i) ~= mu + b_i + b_u + p_u . q_i

``mu`` is the global mean, ``b_i``/``b_u`` are item and user biases learned
from the training split, and ``p_u``/``q_i`` are the leading latent factors of
the bias residuals. Training takes about 2-3 seconds on the MovieLens Latest
Small data and is cached per process, so no artifact file has to be shipped.

Evaluation uses a per-user holdout (each user's latest 20% of ratings by
timestamp), which is stricter than a random row split. ``model_metrics()``
returns RMSE/MAE plus precision@10 for the model against the global-mean,
item-bias, and popularity baselines used in the Insights page.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

FACTORS = 20
HOLDOUT_FRACTION = 0.20
PRECISION_USERS = 120
PRECISION_K = 10
RELEVANT_RATING = 4.0
_SEED = 0


def _rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.sqrt(np.mean((actual - predicted) ** 2)))


def _mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    return float(np.mean(np.abs(actual - predicted)))


def _quality_prior(item_rows, values, n_items):
    """Rating quality and popularity prior used as the ranking baseline."""
    counts = np.bincount(item_rows, minlength=n_items).astype(float)
    averages = np.divide(
        np.bincount(item_rows, weights=values, minlength=n_items),
        counts,
        out=np.zeros(n_items),
        where=counts > 0,
    )
    popularity = np.log1p(counts) / np.log1p(counts.max() or 1.0)
    return popularity, 0.6 * (averages / 5.0) + 0.4 * popularity


def _precision_at_k(items, ratings, test, latent_scores, k, n_users):
    """Mean fraction of the top k unseen picks rated >= 4.0 in the holdout.

    Ranking the raw latent match alone is worse than popularity, because it
    ignores whether a movie is any good. The model is therefore scored the
    way the app uses it: blended with a quality prior.
    """
    rng = np.random.default_rng(_SEED)
    users = np.sort(test["userId"].unique())
    sample = rng.choice(users, size=min(n_users, len(users)), replace=False)

    item_rows = ratings["movieId"].map(
        {movie_id: row for row, movie_id in enumerate(items)}
    )
    train_pairs = item_rows.notna().to_numpy()
    popularity, quality = _quality_prior(
        item_rows[train_pairs].to_numpy().astype(int),
        ratings["rating"].to_numpy()[train_pairs],
        len(items),
    )

    seen = ratings.groupby("userId")["movieId"].apply(set).to_dict()
    relevant = (
        test[test["rating"] >= RELEVANT_RATING]
        .groupby("userId")["movieId"]
        .apply(set)
        .to_dict()
    )

    results = []
    for user_id in sample:
        candidates = np.array(
            [
                row
                for row, movie_id in enumerate(items)
                if movie_id not in seen.get(user_id, set())
            ]
        )
        if candidates.size == 0:
            continue
        truth = relevant.get(user_id, set())
        latent = latent_scores.get(user_id)
        if latent is None:
            continue
        hybrid = 0.65 * quality + 0.35 * ((latent + 1.0) / 2.0)

        def hits(scoring):
            ranked = candidates[np.argsort(-scoring[candidates])[:k]]
            return sum(1 for row in ranked if items[row] in truth) / k

        results.append((hits(popularity), hits(quality), hits(hybrid)))

    if not results:
        return {"popularity": 0.0, "quality": 0.0, "model": 0.0}

    arr = np.array(results)
    return {
        "popularity": float(arr[:, 0].mean()),
        "quality": float(arr[:, 1].mean()),
        "model": float(arr[:, 2].mean()),
    }


def train(ratings: pd.DataFrame) -> dict:
    """Fit the model and return its parameters plus held-out metrics."""
    if ratings.empty:
        raise ValueError("Rating data is required to train the model.")

    ordered = ratings.sort_values(
        ["userId", "timestamp", "movieId"]
    ).reset_index(drop=True)
    per_user = ordered.groupby("userId")["movieId"].transform("size")
    position = ordered.groupby("userId").cumcount()
    holdout = (per_user * HOLDOUT_FRACTION).round().clip(lower=1)
    test_mask = (position >= (per_user - holdout)).to_numpy()

    train = ordered[~test_mask]
    test = ordered[test_mask]

    users = np.sort(train["userId"].unique())
    items = np.sort(ratings["movieId"].unique())
    user_pos = {user_id: row for row, user_id in enumerate(users)}
    item_pos = {movie_id: row for row, movie_id in enumerate(items)}

    user_rows = train["userId"].map(user_pos).to_numpy()
    item_rows = train["movieId"].map(item_pos).to_numpy()
    values = train["rating"].to_numpy(dtype=float)

    mu = float(values.mean())

    item_bias = np.zeros(len(items))
    item_counts = np.bincount(item_rows, minlength=len(items))
    np.add.at(item_bias, item_rows, values - mu)
    item_bias = np.divide(
        item_bias, item_counts, out=np.zeros_like(item_bias), where=item_counts > 0
    )

    user_bias = np.zeros(len(users))
    np.add.at(user_bias, user_rows, values - mu - item_bias[item_rows])
    user_counts = np.bincount(user_rows, minlength=len(users))
    user_bias = np.divide(
        user_bias, user_counts, out=np.zeros_like(user_bias), where=user_counts > 0
    )

    residual = np.zeros((len(users), len(items)))
    residual[user_rows, item_rows] = (
        values - mu - item_bias[item_rows] - user_bias[user_rows]
    )

    u_mat, s_vec, vt_mat = np.linalg.svd(residual, full_matrices=False)
    factors = min(FACTORS, len(s_vec))
    user_factors = u_mat[:, :factors] * s_vec[:factors]
    item_factors = vt_mat[:factors].T

    # Unit-normalised item factors make a session user's taste vector a
    # simple cosine match against the catalogue.
    norms = np.linalg.norm(item_factors, axis=1, keepdims=True)
    unit_item_factors = item_factors / np.maximum(norms, 1e-9)

    test_users = test["userId"].map(user_pos).to_numpy()
    test_items = test["movieId"].map(item_pos).to_numpy()
    known = ~np.isnan(test_users) & ~np.isnan(test_items)
    test_users = test_users[known].astype(int)
    test_items = test_items[known].astype(int)
    actual = test["rating"].to_numpy()[known]

    bias_prediction = np.clip(
        mu + item_bias[test_items] + user_bias[test_users], 0.5, 5.0
    )
    model_prediction = np.clip(
        mu
        + item_bias[test_items]
        + user_bias[test_users]
        + np.einsum(
            "ij,ij->i",
            user_factors[test_users],
            item_factors[test_items],
        ),
        0.5,
        5.0,
    )

    # Rank only by what an anonymous visitor can see: item bias and latent
    # taste, never the user's own bias term.
    latent_scores = {}
    for user_id, group in test.groupby("userId"):
        rows = user_pos.get(user_id)
        if rows is None:
            continue
        latent_scores[user_id] = item_factors @ user_factors[rows]

    precision = _precision_at_k(
        items,
        train,
        test,
        latent_scores,
        PRECISION_K,
        PRECISION_USERS,
    )

    return {
        "mu": mu,
        "item_ids": items,
        "item_bias": item_bias,
        "item_factors": item_factors,
        "unit_item_factors": unit_item_factors,
        "user_factors": user_factors,
        "user_ids": users,
        "user_bias": user_bias,
        "factors": factors,
        "metrics": {
            "rmse_baseline": _rmse(actual, np.full_like(actual, mu)),
            "rmse_item_bias": _rmse(actual, bias_prediction),
            "rmse_model": _rmse(actual, model_prediction),
            "mae_model": _mae(actual, model_prediction),
            "precision_popularity": precision["popularity"],
            "precision_quality": precision["quality"],
            "precision_model": precision["model"],
            "train_ratings": int(len(train)),
            "test_ratings": int(len(test)),
            "users": int(len(users)),
            "items": int(len(items)),
            "factors": int(factors),
            "k": PRECISION_K,
        },
    }


@st.cache_data(show_spinner=False)
def get_model() -> dict:
    """Train once per process and reuse the parameters."""
    from src.data_loader import load_ratings

    return train(load_ratings())


def taste_vector(liked_ids, model: dict | None = None) -> np.ndarray | None:
    """Fold a session user into the latent space from the movies they liked."""
    if not liked_ids:
        return None
    model = model or get_model()
    position = {int(movie_id): row for row, movie_id in enumerate(model["item_ids"])}
    rows = [position[int(movie_id)] for movie_id in liked_ids if int(movie_id) in position]
    if not rows:
        return None
    vector = model["unit_item_factors"][rows].mean(axis=0)
    norm = np.linalg.norm(vector)
    if norm == 0:
        return None
    return vector / norm


def taste_scores(catalog: pd.DataFrame, liked_ids, model: dict | None = None):
    """Return a 0-1 latent taste match for every catalog row, or None."""
    vector = taste_vector(liked_ids, model)
    if vector is None:
        return None
    model = model or get_model()
    position = pd.Series(
        np.arange(len(model["item_ids"])), index=model["item_ids"]
    )
    rows = catalog["movieId"].map(position)
    cosine = np.zeros(len(catalog))
    known = rows.notna().to_numpy()
    if known.any():
        cosine[known] = model["unit_item_factors"][
            rows[known].to_numpy().astype(int)
        ] @ vector
    return (cosine + 1.0) / 2.0


def ranking_scores(
    catalog: pd.DataFrame, liked_ids, model: dict | None = None, quality_weight: float = 0.65
):
    """Taste match blended with the quality prior used in the evaluation.

    Ranking on latent taste alone surfaces obscure titles that happen to sit
    near the user's vector, so the shipped score is the same blend that is
    measured in ``model_metrics()``.
    """
    counts = catalog["rating_count"].fillna(0).to_numpy(dtype=float)
    popularity = np.log1p(counts) / np.log1p(counts.max() or 1.0)
    quality = 0.6 * (
        catalog["avg_rating"].fillna(0).to_numpy(dtype=float) / 5.0
    ) + 0.4 * popularity

    taste = taste_scores(catalog, liked_ids, model)
    if taste is None:
        return quality
    return quality_weight * quality + (1.0 - quality_weight) * taste


def similarity_scores(
    catalog: pd.DataFrame, movie_id, model: dict | None = None
):
    """0-1 latent similarity between one movie and every catalog row."""
    model = model or get_model()
    position = {int(value): row for row, value in enumerate(model["item_ids"])}
    row = position.get(int(movie_id))
    if row is None:
        return None
    vector = model["unit_item_factors"][row]
    lookup = pd.Series(np.arange(len(model["item_ids"])), index=model["item_ids"])
    rows = catalog["movieId"].map(lookup)
    cosine = np.zeros(len(catalog))
    known = rows.notna().to_numpy()
    if known.any():
        cosine[known] = model["unit_item_factors"][
            rows[known].to_numpy().astype(int)
        ] @ vector
    return (cosine + 1.0) / 2.0


def taste_match(movie_id, liked_ids, model: dict | None = None) -> float | None:
    """Latent taste match (0-1) for a single movie, or None without likes."""
    vector = taste_vector(liked_ids, model)
    if vector is None:
        return None
    model = model or get_model()
    position = {int(value): row for row, value in enumerate(model["item_ids"])}
    row = position.get(int(movie_id))
    if row is None:
        return None
    return float((model["unit_item_factors"][row] @ vector + 1.0) / 2.0)


def model_metrics() -> dict | None:
    """Metrics for the Insights page, or None when training is unavailable."""
    try:
        return get_model()["metrics"]
    except Exception:
        return None
