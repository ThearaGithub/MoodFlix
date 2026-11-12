# AGENTS.md

MoodFlix is a single-page Streamlit app. `app.py` is the only entrypoint and contains the sidebar router plus every page; there is no `pages/` directory.

## Run and verify

- Install dependencies with `pip install -r requirements.txt` (unpinned; local environment is Python 3.13 / Streamlit 1.64).
- Run with `python -m streamlit run app.py`. Do not run `python app.py`.
- Health check: `(Invoke-WebRequest http://localhost:8501/_stcore/health).Content` should return `ok`.
- If port 8501 already returns `ok`, reuse that server. After changing `src/`, restart it; Streamlit may keep imported modules cached.
- There is no test suite, linter, typechecker, or lockfile. Syntax-check with `python -m compileall -q app.py src scripts`.
- UI regression checks use `streamlit.testing.v1.AppTest`. AppTest cannot click widgets inside `st.dialog`, and YouTube embeds are read with `at.get("video")`, not `at.video`.

## Architecture

- `src/data_loader.py` builds the cached catalog: it parses `year` from the trailing `(YYYY)` in the title, adds rating stats, then merges the optional `posters.csv` and `links.csv` (`imdbId`, `tmdbId`).
- Cache gotcha: `load_movies`, `load_ratings`, `load_movie_stats`, and `load_catalog` have no TTL; `load_posters` and `load_links` use 300s. Restart the server or call `st.cache_data.clear()` after editing CSVs.
- `src/recommender.py` scores with fixed weights; `randomize=True` samples from the top `n*5` pool. `refresh_queue()` in `app.py` first adds the current deck to `session_state.seen`, which enforces the no-repeat behavior.
- `src/model.py` trains a biased matrix factorisation (truncated SVD, 20 factors) on `ratings.csv` and supplies the 15% personal-match term through the `personal_scores` argument of `recommend()`. Training takes ~2.5s and is wrapped in `st.cache_data`, so restarting the server retrains. `_collaborative_scores()` remains the fallback when no model/personal scores are passed. Metrics are computed on a per-user holdout (latest 20% by timestamp); `python scripts/evaluate_model.py` reproduces them and writes `data/model_metrics.json`. The Insights page renders the same numbers, so keep them in sync with the README table.
- Do not rank by raw latent similarity alone: it ignores quality and scores below the popularity baseline on precision@10. The evaluated and shipped blend is `0.65 * quality_prior + 0.35 * latent`, and inside `recommend()` the latent match keeps the existing 15% weight.
- `src/ui.py` owns all custom CSS and reusable HTML components. Poster tiles intentionally have no visible details button: each tile overlays an invisible `st.button` on the poster inside `st.container(key="mfposter_<prefix>_<id>")`, and the CSS targets `[class*="st-key-mfposter_"]`. Preserve that key prefix and CSS when changing the grid.
- The theme is split: `.streamlit/config.toml` sets Streamlit colors, while gradients, cards, and button styling live in `inject_css()` in `src/ui.py`. Theme changes usually touch both. `assets/logo.jpe` is both the page icon and the sidebar image.
- Navigation, likes, watchlist, queue, and seen history are all session-only (`st.session_state`); there is no database or account system.

## Extras and external APIs

- `src/extras.py` uses TMDB first when credentials exist. Without credentials it falls back to Bing video search for trailers and Wikipedia/Wikidata for cast. A TMDB key must never be required for the details dialog to work.
- Trailer and cast results are cached for 6 hours. `_read_response()` enforces wall-clock deadlines because socket timeouts reset per chunk; do not replace it with plain `response.read()`.
- Bing parsing is HTML scraping: each video card's `mmeta` JSON supplies the URL and its `aria-label` supplies the title. If trailers break, inspect `_bing_video_search()` first; the markup, not the scoring, is the fragile part.
- `data/links.csv` stores IMDb IDs as bare digits. `_normalise_imdb_id()` adds the `tt` prefix and zero-pads; do not assume `tt...` values in the CSV.
- `themoviedb.org` returns 403 to scrapers. Use only `api.themoviedb.org` with a key or bearer token.

## Data and credentials

- The committed CSVs in `data/` are required. `python scripts/download_data.py` re-downloads `movies.csv`, `ratings.csv`, `tags.csv`, and `links.csv`, but does not create `posters.csv`.
- `data/posters.csv` is optional. `python scripts/fetch_posters.py` generates it and requires `TMDB_API_KEY` or `TMDB_API_TOKEN` in `.streamlit/secrets.toml` or the environment. It is incremental; flags are `--workers N`, `--limit N`, and `--refresh`.
- `.streamlit/secrets.toml` is gitignored; use `.streamlit/secrets.toml.example` as the template.

## Behavior to preserve

- Search is case-insensitive substring matching (`regex=False`) with 24 results per page; clicking a poster opens the details dialog.
- The dialog always shows Trailer and Cast sections with graceful fallbacks, plus the watchlist action.
- Keep `README.md` in sync with user-visible behavior.
