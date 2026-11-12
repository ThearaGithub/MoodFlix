# MoodFlix

Mood-first movie discovery built with Streamlit, Pandas, and NumPy.

MoodFlix learns from the movies you like, blends content similarity, rating quality, popularity, collaborative signals, and mood match, then serves a swipeable shortlist with a Netflix-inspired red-and-black theme.

## Features

- Netflix-style dark theme with a custom MoodFlix logo and a slowly drifting red gradient background
- Mood-based discovery across 8 moods (Happy, Excited, Relaxed, Romantic, Thoughtful, Scared, Nostalgic, Sad)
- Optional camera mood detection: take one photo and the app suggests a mood
- Swipe-style Like / Pass deck
- Randomized recommendation batches: every new batch is sampled from the best candidates, so the same movie does not come up every time
- No repeats within a session — movies already shown, liked, or passed are excluded from later batches
- Content-based recommendations from genres
- Trained latent-factor model (biased matrix factorisation / SVD) that supplies the personal match signal, evaluated on held-out ratings
- Collaborative filtering from MovieLens ratings as the model's fallback
- Case-insensitive search with poster grids, genre filters, and pagination
- Click any poster to open a detail dialog with trailer, cast, poster, rating, genres, and tags
- Trailer playback and top-billed cast with photos
- Watchlist with CSV export
- TMDB movie posters with a graceful fallback
- Model insights and catalog statistics
- Session-only preferences (no accounts, no tracking)

## Preview

![MoodFlix demo: Home, Discover, the recommendation model and catalog analytics](assets/preview.gif)

The loop walks through the four pages that matter: **Home** (catalog stats and the
"You may like" row), **Discover** (mood picker, the optional camera panel, and the
swipe card), **Model insights** (the recommendation model's measured error and
ranking quality) and the catalog charts. Stills live in `assets/`:
`home.png`, `discover.png`, `model.png`, `insights.png`.

## Tech Stack

- Python
- Streamlit
- Pandas
- NumPy
- BeautifulSoup
- MovieLens Latest Small dataset

## Project Structure

```text
MoodFlix/
├── app.py
├── requirements.txt
├── README.md
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── assets/
│   ├── logo.jpe
│   ├── preview.gif
│   ├── home.png
│   ├── discover.png
│   ├── model.png
│   └── insights.png
├── data/
│   ├── movies.csv
│   ├── ratings.csv
│   ├── tags.csv
│   ├── links.csv
│   └── posters.csv
├── scripts/
│   ├── download_data.py
│   ├── evaluate_model.py
│   └── fetch_posters.py
├── requirements-vision.txt
└── src/
    ├── data_loader.py
    ├── extras.py
    ├── model.py
    ├── mood.py
    ├── recommender.py
    ├── ui.py
    └── vision.py
```

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

The MovieLens data is included. To re-download it:

```bash
python scripts/download_data.py
```

Poster data is optional. To generate the cached TMDB posters, copy
`.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, add your TMDB
API key, and run:

```bash
python scripts/fetch_posters.py
```

Trailers and cast work without any key: the app searches Bing video
results for a trailer and reads cast information from Wikipedia/Wikidata.
Adding a TMDB key makes the lookups richer and faster — TMDB is used first,
and the public sources fill in anything missing.

Run the app:

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

## Theme

The look is defined in two places:

- `.streamlit/config.toml` sets the Streamlit palette: Netflix red `#E50914`
  on a dark red-black background, dark panels, and light text.
- `src/ui.py` injects the custom CSS: red gradient page titles, red-tinted
  cards and posters, red buttons, red metric panels, hover effects, and the
  logo styling.

The MoodFlix logo (`assets/logo.jpe`) is shown in the sidebar and used as the
browser tab icon.

## Search

The Search page matches any part of a title, ignoring upper and lower case
(`toy`, `TOY`, and `ToY` all find Toy Story). Movies can be filtered further by
genre. Every match is displayed as a poster tile; results are paginated
24 movies at a time, so even a broad query like "the" (over 3,000 matches) is
fully browsable. Clicking any poster opens a movie-details dialog with the
poster, rating, genres, tags, an embedded trailer, top-billed cast (with
photos when available), and an **Add to watchlist** button.

## Camera Mood Detection (optional)

The Discover page has a **Detect my mood from a photo** panel. Take one photo
with your webcam and a pre-trained facial-expression classifier
([DeepFace](https://github.com/serengil/deepface)) guesses your expression,
shows the confidence, and suggests a mood. You stay in control: the mood
buttons always override the guess. The panel is open by default, so the
browser asks for camera access when Discover loads — nothing is captured or
analysed until you press **Take Photo**, and denying access leaves the rest of
the page fully usable.

The camera needs the optional extras:

```bash
pip install -r requirements-vision.txt
```

That pulls in TensorFlow, so it is a large download (roughly 600 MB) and is
kept out of `requirements.txt`; the app runs normally without it and the panel
shows an install hint instead.

The preview and the captured photo are mirrored, like a bathroom mirror, so
the image matches what you see in the camera. The mirror is a display effect
only; the frame handed to the model is unchanged.

Expressions map onto six of the eight moods: happy to Happy, surprise and
anger to Excited, fear to Scared, disgust to Thoughtful, sadness to Sad, and
neutral to Relaxed. Romantic and Nostalgic have no facial signal, so they stay
manual.

**Privacy:** the photo is analysed on your machine, deleted immediately, and
never uploaded or stored. Accuracy is a guess, not a diagnosis — webcam
lighting and head angle change the result, which is why the manual picker is
always there.

## You May Like

Once you have liked at least one movie, the **Home** page shows a "You may
like" row: the six movies with the best combination of your latent taste match
and rating quality. Before that, the row explains that liking a few movies in
Discover will fill it. Clicking a poster opens the same details dialog.

## Movie Details and Extras

The dialog shows a plot description, a red **taste-match meter** for the model
score (once you have liked something), the trailer, the cast, and a
**You may like** grid of four model picks that can be clicked through to their
own details.

Clicking a poster opens a dialog with the poster, a short plot description, the
top-billed cast as photo cards, an embedded trailer, and a "You may like" row
of four model picks. Lookups are cached for six hours per movie, so reopening
the same title is instant.

Descriptions come from TMDB when credentials exist and from the Wikipedia page
summary otherwise. If neither is available the dialog says so instead of
breaking.

- With TMDB credentials, cast and trailers come from TMDB first.
- Without credentials, the app falls back to Bing video search (which links to
  YouTube trailers) and Wikipedia/Wikidata for the cast.
- If a trailer or cast list is unavailable, the dialog shows a friendly
  fallback instead of an error.

## How Recommendations Work

The score for each candidate movie is:

```text
45% content similarity
20% rating quality
10% popularity
15% latent-factor personal match
10% mood match
```

Content similarity compares genre profiles of liked movies with the catalog. The personal match comes from a model (see below); when the model is unavailable it falls back to finding MovieLens users with similar taste based on the movies you liked.

### The recommendation model

`src/model.py` trains a biased matrix factorisation with a truncated SVD on
`ratings.csv`:

```text
rating(user, movie) ≈ global mean + movie bias + user bias + user factors · movie factors
```

20 latent factors, trained in about 2.5 seconds and cached in the running app,
so nothing has to be shipped as a model file. Your likes are folded into the
latent space at recommendation time, which gives every deck a personal match
score without needing an account.

Evaluation uses a per-user holdout: the latest 20% of each user's ratings by
timestamp (80,672 train / 20,164 test). Reproduce the numbers with:

```bash
python scripts/evaluate_model.py
```

| Ranking | Precision@10 |
| --- | --- |
| Popularity | 0.050 |
| Rating quality + popularity | 0.055 |
| Model (latent taste + quality) | 0.062 |

For rating prediction the model reaches **RMSE 0.935 / MAE 0.713**, against
1.069 for the global-mean baseline and 0.939 for movie and user biases alone.
The Insights page shows the same metrics. Ranking by latent match alone is
worse than popularity, because it ignores whether a movie is any good — which
is why the app blends it with the quality prior instead.

### Random batches and no repeats

After scoring, MoodFlix takes the top 100 candidates and randomly samples 20 for
the deck. That keeps quality high while making each mood change or
**New recommendations** click produce a different set of movies.

Every movie dealt into the deck is remembered for the session, and liked,
passed, and already-shown movies are excluded from future batches. When a batch
runs out it refills automatically with fresh unseen movies. **Start over** on
the Discover page clears passes and history if you want to replay the catalog.

## Data

MovieLens Latest Small dataset from GroupLens Research:

```text
https://grouplens.org/datasets/movielens/
```

Poster images courtesy of TMDB. This product uses the TMDB API but is not
endorsed or certified by TMDB.

Trailer playback uses YouTube embeds. Cast information comes from Wikipedia
and Wikidata when no TMDB key is configured, and from TMDB when one is.

## Team

- Khon Sotheara
- Cheang Youpheng
- Chea Sela
- Khann Udomvirak

## Roadmap

- Optional webcam mood detection with a manual fallback
- User accounts and SQLite persistence
- Precision@k and RMSE evaluation dashboard
- Deployment
