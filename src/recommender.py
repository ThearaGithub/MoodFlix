import numpy as np
import pandas as pd

from src.mood import mood_genres


def _genre_matrix(catalog):
    return catalog["genres"].fillna("").str.get_dummies(sep="|").astype(float)


def _content_scores(matrix, profile):
    norms = np.linalg.norm(matrix, axis=1)
    profile_norm = np.linalg.norm(profile)
    if profile_norm == 0 or norms.max() == 0:
        return np.zeros(len(matrix))
    return (matrix @ profile) / (norms * profile_norm + 1e-9)


def _collaborative_scores(catalog, ratings, liked_ids):
    if ratings.empty or not liked_ids:
        return np.zeros(len(catalog))

    pivot = ratings.pivot_table(index="userId", columns="movieId", values="rating")
    liked_columns = [movie_id for movie_id in liked_ids if movie_id in pivot.columns]
    if not liked_columns:
        return np.zeros(len(catalog))

    subset = pivot[liked_columns].dropna(how="all")
    if subset.empty:
        return np.zeros(len(catalog))
    subset = subset.fillna(0.0)

    pseudo_user = np.full(len(liked_columns), 5.0)
    norms = np.linalg.norm(subset.to_numpy(), axis=1)
    similarities = (subset.to_numpy() @ pseudo_user) / (
        norms * np.linalg.norm(pseudo_user) + 1e-9
    )
    similarities = pd.Series(similarities, index=subset.index)
    top_users = similarities.sort_values(ascending=False).head(30)
    top_users = top_users[top_users > 0]
    if top_users.empty:
        return np.zeros(len(catalog))

    weighted = pivot.loc[top_users.index].mul(top_users, axis=0).sum(axis=0)
    weighted = weighted / top_users.sum()
    scores = catalog["movieId"].map(weighted).fillna(0.0).to_numpy()
    return scores / 5.0


def recommend(
    catalog,
    ratings,
    liked_ids,
    disliked_ids,
    mood=None,
    n=12,
    exclude_ids=None,
    randomize=False,
    pool_size=None,
    personal_scores=None,
):
    if catalog.empty:
        return catalog

    matrix = _genre_matrix(catalog)
    liked_index = catalog.index[catalog["movieId"].isin(liked_ids)]
    if len(liked_index) > 0:
        profile = matrix.loc[liked_index].mean(axis=0).to_numpy()
    else:
        profile = np.zeros(matrix.shape[1])
    content = _content_scores(matrix.to_numpy(), profile)

    rating_score = catalog["avg_rating"].fillna(0).to_numpy() / 5.0
    counts = catalog["rating_count"].fillna(0).to_numpy()
    if counts.max() > 0:
        popularity = np.log1p(counts) / np.log1p(counts.max())
    else:
        popularity = np.zeros_like(counts)

    # The latent-factor model supplies the personal term once the session has
    # likes; the rating-based heuristic stays as the fallback so the deck
    # never depends on the model being available.
    if personal_scores is not None:
        collaborative = np.asarray(personal_scores, dtype=float)
    else:
        collaborative = _collaborative_scores(catalog, ratings, liked_ids)

    mood_score = np.zeros(len(catalog))
    selected_genres = mood_genres(mood) if mood else []
    if selected_genres:
        mood_mask = catalog["genres"].fillna("").apply(
            lambda value: any(genre in value.split("|") for genre in selected_genres)
        )
        mood_score = mood_mask.to_numpy().astype(float)

    score = (
        0.45 * content
        + 0.20 * rating_score
        + 0.10 * popularity
        + 0.15 * collaborative
        + 0.10 * mood_score
    )

    blocked = set(liked_ids) | set(disliked_ids)
    if exclude_ids:
        blocked |= set(exclude_ids)

    candidates = catalog.assign(score=score)
    candidates = candidates[~candidates["movieId"].isin(blocked)]

    if selected_genres:
        mood_candidates = candidates[
            candidates["genres"].fillna("").apply(
                lambda value: any(genre in value.split("|") for genre in selected_genres)
            )
        ]
        if len(mood_candidates) >= n:
            candidates = mood_candidates

    candidates = candidates.sort_values(
        ["score", "rating_count"], ascending=False
    )

    if randomize:
        pool_size = max(int(pool_size or n * 5), n)
        pool = candidates.head(pool_size)
        if len(pool) > n:
            return pool.sample(n=n)
        return pool.sample(frac=1.0)

    return candidates.head(n)
