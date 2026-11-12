# AGENTS.md

MoodFlix is a single-page Streamlit app. `app.py` is the only entrypoint and contains the sidebar router plus every page; there is no `pages/` directory.

## Run and verify

- Install dependencies with `pip install -r requirements.txt` (unpinned; local environment is Python 3.13 / Streamlit 1.67).
- Run with `python -m streamlit run app.py`. Do not run `python app.py`.
- Health check: `(Invoke-WebRequest http://localhost:8501/_stcore/health).Content` should return `ok`.
- If port 8501 already returns `ok`, reuse that server. After changing `src/`, restart it; Streamlit may keep imported modules cached.
- There is no test suite, linter, typechecker, or lockfile. Syntax-check with `python -m compileall -q app.py src scripts`.
- Webcam mood detection is optional; install `requirements-vision.txt` to enable it (large TensorFlow download). Without it the Discover panel shows an install hint and everything else works.
- UI regression checks use `streamlit.testing.v1.AppTest`. AppTest cannot click widgets inside `st.dialog`, and YouTube embeds are read with `at.get("video")`, not `at.video`.

## Architecture

- `src/data_loader.py` builds the cached catalog: it parses `year` from the trailing `(YYYY)` in the title, adds rating stats, then merges the optional `posters.csv` and `links.csv` (`imdbId`, `tmdbId`).
- Cache gotcha: `load_movies`, `load_ratings`, `load_movie_stats`, and `load_catalog` have no TTL; `load_posters` and `load_links` use 300s. Restart the server or call `st.cache_data.clear()` after editing CSVs.
- `src/recommender.py` scores with fixed weights; `randomize=True` samples from the top `n*5` pool. `refresh_queue()` in `app.py` first adds the current deck to `session_state.seen`, which enforces the no-repeat behavior.
- `src/model.py` trains a biased matrix factorisation (truncated SVD, 20 factors) on `ratings.csv` and supplies the 15% personal-match term through the `personal_scores` argument of `recommend()`. Training takes ~2.5s and is wrapped in `st.cache_data`, so restarting the server retrains. `_collaborative_scores()` remains the fallback when no model/personal scores are passed. Metrics are computed on a per-user holdout (latest 20% by timestamp); `python scripts/evaluate_model.py` reproduces them and writes `data/model_metrics.json`. The Insights page renders the same numbers, so keep them in sync with the README table.
- Do not rank by raw latent similarity alone: it ignores quality and scores below the popularity baseline on precision@10. The evaluated and shipped blend is `0.65 * quality_prior + 0.35 * latent`, and inside `recommend()` the latent match keeps the existing 15% weight.
- Model helpers used by the UI: `taste_scores()` (0-1 match per catalog row), `taste_match()` (one movie), `ranking_scores()` (taste blended with the quality prior), `similarity_scores()` (latent similarity to one movie). `may_like_picks()` in `app.py` wraps them and excludes liked/disliked movies; it powers the Home row and the in-dialog "You may like" grid. Because model scores alone surface obscure low-rated titles, always route user-facing picks through `ranking_scores()`, not `taste_scores()`.
- `src/ui.py` owns all custom CSS and reusable HTML components. Poster tiles intentionally have no visible details button: each tile overlays an invisible `st.button` on the poster inside `st.container(key="mfposter_<prefix>_<id>")`, and the CSS targets `[class*="st-key-mfposter_"]`. Preserve that key prefix and CSS when changing the grid.
- The theme is split: `.streamlit/config.toml` sets Streamlit colors, while gradients, cards, and button styling live in `inject_css()` in `src/ui.py`. Theme changes usually touch both. `assets/logo.jpe` is both the page icon and the sidebar image.
- The animated background is three fixed-attachment background layers on `.stApp` whose `background-position` is animated (`mf-drift`). Two things to keep in mind: positions must stay in `px`/`calc()` because percentage positions resolve against the multi-thousand-pixel page body and visibly do not move; and separate glow `<div>`s with `z-index: -1` render *behind* `.stApp`'s own background, so they are not an option. One static red layer stays put so the page never goes black mid-cycle. `prefers-reduced-motion` disables the animation.
- `src/ui.py` also provides `overview_block()` (plot paragraph), `taste_meter()` (red 0-100 bar for the model score), `movie_card()`, `clickable_movie_card()`, `poster_grid()`, `trailer_block()`, `cast_grid()`, and `watch_providers_block()` (provider logo chips, styled by the `.mf-watch*` CSS). When building HTML for `st.markdown`, keep each block on a single line with no blank lines: Markdown ends an HTML block at a blank line and renders the rest as a code block (this is what once broke the cast grid).
- Navigation, likes, watchlist, queue, and seen history are all session-only (`st.session_state`); there is no database or account system.

## Camera mood detection

- `src/vision.py` is optional: it imports DeepFace lazily, so the app and `requirements.txt` stay light. The camera panel on Discover checks `is_available()` (cached with `lru_cache`) and shows `INSTALL_HINT` when `requirements-vision.txt` is not installed. Do not move DeepFace into `requirements.txt` or import it at module scope.
- `suggest_mood()` maps the top emotion onto a mood via `EMOTION_TO_MOOD`; `Romantic`, `Nostalgic`, and `Thoughtful` do not come from faces. The manual mood radio is the source of truth: the camera only offers a `Use <mood>` button whose callback (`set_mood()`) sets `session_state.mood` and clears the queue. Never set `session_state.mood` after the radio widget is instantiated — use the callback.
- Privacy contract: the frame goes to a temp file only because DeepFace takes a path, and that file is deleted in `finally`. Nothing is uploaded, cached, or kept in `session_state`; keep it that way and keep the About/README wording accurate.
- The camera expander is open by default (`expanded=True`), so the browser shows its camera-permission prompt as soon as Discover loads. No frame is captured until the user presses Take Photo, and denying permission must leave the rest of the page working — that is why the copy says "nothing is captured until you take a photo" rather than "the feature is off".
- `st.camera_input` cannot be exercised from `AppTest` and needs a real webcam plus `localhost`/HTTPS, so a UI regression test only covers the install-hint branch. Verify the camera path by hand.
- The webcam preview is mirrored with `transform: scaleX(-1)` on `[data-testid="stCameraInput"] video, img` in `inject_css()`. It is display-only: the captured frame sent to the model is unchanged, so do not "fix" the mirror in the image bytes.

## Extras and external APIs

- `src/extras.py` uses TMDB first when credentials exist. Without credentials it falls back to Bing video search for trailers, Wikipedia/Wikidata for cast, and the Wikipedia page-summary endpoint for the plot description. A TMDB key must never be required for the details dialog to work.
- `get_movie_extras()` returns `{"cast", "overview", "trailer", "watch", "source"}`. TMDB supplies `overview` when configured; otherwise `_web_description()` resolves the article through Wikidata/`_wikipedia_search()` and reads the summary extract. A missing description renders a caption, never an error.
- `watch` is always a dict (`region`, `available`, `link`, `groups`, `search_url`), built by `_watch_providers()`. `groups` maps `flatrate`/`free`/`ads`/`rent`/`buy` to `[{"name", "logo_url"}]`. The TMDB request already appends `watch/providers`, so there is no extra HTTP call; region comes from `TMDB_WATCH_REGION` (default `US`). With no credentials or no offers, `available` is false and `search_url` is a JustWatch search link — keyless installs must still show that fallback instead of an empty section.
- Trailer, cast, and description results are cached for 6 hours. `_read_response()` enforces wall-clock deadlines because socket timeouts reset per chunk; do not replace it with plain `response.read()`.
- Bing parsing is HTML scraping: each video card's `mmeta` JSON supplies the URL and its `aria-label` supplies the title. If trailers break, inspect `_bing_video_search()` first; the markup, not the scoring, is the fragile part.
- `data/links.csv` stores IMDb IDs as bare digits. `_normalise_imdb_id()` adds the `tt` prefix and zero-pads; do not assume `tt...` values in the CSV.
- `themoviedb.org` returns 403 to scrapers. Use only `api.themoviedb.org` with a key or bearer token.

## Data and credentials

- The committed CSVs in `data/` are required. `python scripts/download_data.py` re-downloads `movies.csv`, `ratings.csv`, `tags.csv`, and `links.csv`, but does not create `posters.csv`.
- `data/posters.csv` is optional. `python scripts/fetch_posters.py` generates it and requires `TMDB_API_KEY` or `TMDB_API_TOKEN` in `.streamlit/secrets.toml` or the environment. It is incremental; flags are `--workers N`, `--limit N`, and `--refresh`.
- `.streamlit/secrets.toml` is gitignored; use `.streamlit/secrets.toml.example` as the template.

## Behavior to preserve

- Search is case-insensitive substring matching (`regex=False`) with 24 results per page; clicking a poster opens the details dialog.
- The details dialog always shows, in order: the movie card, the plot description (or a fallback caption), a taste-match meter once the session has likes, Trailer, Cast, Where to watch, the watchlist action, and a "You may like" grid of four model picks. Every section needs a graceful fallback.
- The Home page has a "You may like" row: a hint before the first like, six clickable poster tiles after it.
- Keep `README.md` in sync with user-visible behavior.
