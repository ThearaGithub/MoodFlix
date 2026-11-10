import argparse
import json
import os
import ssl
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import certifi
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
POSTERS_PATH = DATA_DIR / "posters.csv"
SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def load_credentials():
    key = os.getenv("TMDB_API_KEY", "").strip()
    token = os.getenv("TMDB_API_TOKEN", "").strip()
    if SECRETS_PATH.exists():
        secrets = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
        key = key or str(secrets.get("TMDB_API_KEY", "")).strip()
        token = token or str(secrets.get("TMDB_API_TOKEN", "")).strip()
    return key, token


def load_links():
    links = pd.read_csv(DATA_DIR / "links.csv", dtype={"tmdbId": "Int64"})
    links = links.dropna(subset=["tmdbId"])
    links["tmdbId"] = links["tmdbId"].astype(int)
    return links[["movieId", "tmdbId"]].drop_duplicates("movieId")


def load_existing():
    if not POSTERS_PATH.exists():
        return {}
    posters = pd.read_csv(POSTERS_PATH)
    required = {"movieId", "tmdbId", "poster_url"}
    if not required.issubset(posters.columns):
        return {}
    return {
        int(row.movieId): (
            int(row.movieId),
            int(row.tmdbId),
            "" if pd.isna(row.poster_url) else str(row.poster_url).strip(),
        )
        for row in posters.itertuples()
    }


def save_rows(rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(
        rows,
        columns=["movieId", "tmdbId", "poster_url"],
    ).sort_values("movieId")
    frame.to_csv(POSTERS_PATH, index=False)


def request_poster(movie_id, tmdb_id, key, token, retries=3):
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    headers = {"User-Agent": "MoodFlix/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        url = f"{url}?{urllib.parse.urlencode({'api_key': key})}"

    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(
                request, context=SSL_CONTEXT, timeout=30
            ) as response:
                payload = json.load(response)
            path = payload.get("poster_path")
            poster_url = f"{IMAGE_BASE}{path}" if path else ""
            return int(movie_id), int(tmdb_id), poster_url
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise RuntimeError("TMDB rejected the API key or token.") from exc
            if exc.code == 404:
                return int(movie_id), int(tmdb_id), ""
            if exc.code == 429:
                time.sleep(2**attempt)
                continue
            if attempt == retries - 1:
                raise
            time.sleep(1 + attempt)
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries - 1:
                raise
            time.sleep(1 + attempt)

    return int(movie_id), int(tmdb_id), ""


def main():
    parser = argparse.ArgumentParser(
        description="Fetch TMDB poster URLs for the MovieLens catalog."
    )
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()

    key, token = load_credentials()
    if not key and not token:
        raise SystemExit(
            "No TMDB credentials found. Add TMDB_API_KEY to "
            ".streamlit/secrets.toml or set the environment variable."
        )

    links = load_links()
    rows = {} if args.refresh else load_existing()
    todo = links[~links["movieId"].isin(rows)]
    if args.limit:
        todo = todo.head(args.limit)

    if todo.empty:
        print(f"Nothing to do. {len(rows):,} poster rows already cached.")
        return

    print(f"Fetching posters for {len(todo):,} movies with {args.workers} workers...")
    completed = 0
    try:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = [
                pool.submit(
                    request_poster,
                    int(row.movieId),
                    int(row.tmdbId),
                    key,
                    token,
                )
                for row in todo.itertuples()
            ]
            for future in as_completed(futures):
                movie_id, tmdb_id, poster_url = future.result()
                rows[movie_id] = (movie_id, tmdb_id, poster_url)
                completed += 1
                if completed % 100 == 0:
                    save_rows(rows.values())
                    print(f"  {completed:,}/{len(todo):,} saved")
    finally:
        save_rows(rows.values())

    with_posters = sum(1 for _, _, url in rows.values() if url)
    print(
        f"Done. {with_posters:,} posters cached out of {len(rows):,} movies "
        f"in {POSTERS_PATH}."
    )


if __name__ == "__main__":
    main()
