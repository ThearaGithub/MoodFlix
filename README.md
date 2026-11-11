# MoodFlix

Mood-first movie discovery built with Streamlit, Pandas, and NumPy.

MoodFlix learns from the movies you like, blends content similarity, rating quality, popularity, collaborative signals, and mood match, then serves a swipeable shortlist with a Netflix-inspired red-and-black theme.

## Features

- Netflix-style dark theme with a custom MoodFlix logo
- Mood-based discovery across 8 moods (Happy, Excited, Relaxed, Romantic, Thoughtful, Scared, Nostalgic, Sad)
- Swipe-style Like / Pass deck
- Randomized recommendation batches: every new batch is sampled from the best candidates, so the same movie does not come up every time
- No repeats within a session — movies already shown, liked, or passed are excluded from later batches
- Content-based recommendations from genres
- Collaborative filtering from MovieLens ratings
- Case-insensitive search with poster grids, genre filters, and pagination
- Movie detail cards with posters, ratings, and tags
- Watchlist with CSV export
- TMDB movie posters with a graceful fallback
- Model insights and catalog statistics
- Session-only preferences (no accounts, no tracking)

## Preview

![MoodFlix demo](assets/preview.gif)

## Tech Stack

- Python
- Streamlit
- Pandas
- NumPy
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
│   └── insights.png
├── data/
│   ├── movies.csv
│   ├── ratings.csv
│   ├── tags.csv
│   ├── links.csv
│   └── posters.csv
├── scripts/
│   ├── download_data.py
│   └── fetch_posters.py
└── src/
    ├── data_loader.py
    ├── mood.py
    ├── recommender.py
    └── ui.py
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
poster, rating, genres, tags, and an **Add to watchlist** button.

## How Recommendations Work

The score for each candidate movie is:

```text
45% content similarity
20% rating quality
10% popularity
15% collaborative signal
10% mood match
```

Content similarity compares genre profiles of liked movies with the catalog. The collaborative signal finds MovieLens users with similar taste based on the movies you liked.

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
