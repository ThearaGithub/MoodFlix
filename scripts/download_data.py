import io
import ssl
import urllib.request
import zipfile
from pathlib import Path

import certifi

DATA_URL = "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FILES = ["movies.csv", "ratings.csv", "tags.csv"]


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {DATA_URL} ...")
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(DATA_URL, context=context) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))

    for name in FILES:
        target = DATA_DIR / name
        with archive.open(f"ml-latest-small/{name}") as source:
            target.write_bytes(source.read())
        print(f"Saved {target}")

    print("MovieLens data is ready.")


if __name__ == "__main__":
    main()
