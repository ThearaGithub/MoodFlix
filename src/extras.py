"""Trailer, cast, and streaming-availability lookups for MoodFlix dialogs.

TMDB is used automatically when a key or bearer token is configured in
``.streamlit/secrets.toml`` (or the ``TMDB_API_KEY`` / ``TMDB_API_TOKEN``
environment variables). When no credentials are available the module falls
back to Bing video search for trailers and Wikipedia/Wikidata for cast and
actor photos, so the feature still works out of the box.

The public helpers are cached per Streamlit session, so reopening the same
movie does not hit the network again.
"""

from __future__ import annotations

import html
import json
import math
import os
import re
import ssl
import time
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import certifi
import streamlit as st
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w185"
WATCH_LOGO_BASE = "https://image.tmdb.org/t/p/w92"
JUSTWATCH_BASE = "https://www.justwatch.com"
DEFAULT_WATCH_REGION = "US"
# JustWatch uses a few regional slugs that differ from the ISO code.
JUSTWATCH_REGION_SLUGS = {"GB": "uk"}
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
TIMEOUT = 8
TOTAL_TIMEOUT = 12
BING_TIMEOUT = 6
BING_TOTAL_TIMEOUT = 8
YOUTUBE_TIMEOUT = 6
YOUTUBE_TOTAL_TIMEOUT = 9
YOUTUBE_API_URL = "https://www.youtube.com/youtubei/v1/search"
YOUTUBE_WEB_KEY = os.getenv("YOUTUBE_WEB_KEY") or (
    "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
)
USER_AGENT = (
    "MoodFlix/1.0 (educational movie recommender; "
    "https://github.com/ThearaGithub/MoodFlix)"
)
_YOUTUBE_COOLDOWN_UNTIL = 0.0
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
_BING_CARD_RE = re.compile(
    r'mmeta="([^"]+)"(?:(?!mmeta=").)*?aria-label="([^"]+)"',
    re.S,
)

_TRAILER_BAD_WORDS = (
    "reaction",
    "review",
    "breakdown",
    "explained",
    "ending",
    "interview",
    "parody",
    "fan made",
    "fan-made",
    "commentary",
    "clip",
    "scene",
    "behind the scenes",
    "bloopers",
    "video game",
    "game trailer",
)
_TRAILER_REJECT_WORDS = (
    "non official",
    "non-official",
    "unofficial",
    "concept trailer",
    "fan trailer",
)
_STOP_WORDS = {
    "the",
    "a",
    "an",
    "of",
    "and",
    "in",
    "to",
    "on",
    "for",
    "with",
    "from",
}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _read_response(response, total_timeout: float) -> str:
    """Read a response while enforcing a wall-clock deadline.

    Socket timeouts reset every time a byte arrives, so a server that
    trickles data can keep a request alive far longer than its timeout.
    The deadline here bounds the whole body read.
    """
    start = time.monotonic()
    chunks = []
    while True:
        if time.monotonic() - start > total_timeout:
            raise TimeoutError("Response exceeded the time budget.")
        chunk = response.read(64 * 1024)
        if not chunk:
            break
        chunks.append(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace")


def _read(
    url: str,
    headers: dict | None = None,
    timeout: int = TIMEOUT,
    total_timeout: int = TOTAL_TIMEOUT,
) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(
        request, timeout=timeout, context=SSL_CONTEXT
    ) as response:
        return _read_response(response, total_timeout)


def _get_json(
    url: str, headers: dict | None = None, attempts: int = 2
) -> dict:
    last_error = None
    for attempt in range(attempts):
        try:
            return json.loads(_read(url, headers=headers))
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in (429, 500, 502, 503, 504) and attempt + 1 < attempts:
                time.sleep(1.0 + attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.8 + attempt)
                continue
            raise
    raise last_error  # pragma: no cover - defensive


def _wiki_api(params: dict) -> dict:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        params
    )
    return _get_json(url, attempts=1)


# ---------------------------------------------------------------------------
# TMDB (used when credentials exist)
# ---------------------------------------------------------------------------


def _tmdb_credentials() -> tuple[str, str]:
    key = os.getenv("TMDB_API_KEY", "").strip()
    token = os.getenv("TMDB_API_TOKEN", "").strip()

    if SECRETS_PATH.exists():
        try:
            secrets = tomllib.loads(SECRETS_PATH.read_text(encoding="utf-8"))
            key = key or str(secrets.get("TMDB_API_KEY", "")).strip()
            token = token or str(secrets.get("TMDB_API_TOKEN", "")).strip()
        except (OSError, tomllib.TOMLDecodeError):
            pass

    try:
        key = key or str(st.secrets.get("TMDB_API_KEY", "")).strip()
        token = token or str(st.secrets.get("TMDB_API_TOKEN", "")).strip()
    except Exception:
        # st.secrets raises when no secrets file is configured.
        pass

    return key, token


def _watch_region() -> str:
    """Region used for streaming availability (``TMDB_WATCH_REGION``)."""
    region = os.getenv("TMDB_WATCH_REGION", "").strip()

    if not region and SECRETS_PATH.exists():
        try:
            secrets = tomllib.loads(
                SECRETS_PATH.read_text(encoding="utf-8")
            )
            region = str(secrets.get("TMDB_WATCH_REGION", "")).strip()
        except (OSError, tomllib.TOMLDecodeError):
            pass

    if not region:
        try:
            region = str(st.secrets.get("TMDB_WATCH_REGION", "")).strip()
        except Exception:
            # st.secrets raises when no secrets file is configured.
            pass

    region = region.upper()[:2]
    return region if len(region) == 2 and region.isalpha() else DEFAULT_WATCH_REGION


def _justwatch_search_url(region: str, title: str, year: int | None) -> str:
    """Keyless fallback: a JustWatch search page for this title."""
    slug = JUSTWATCH_REGION_SLUGS.get(region, region.lower())
    # Catalog titles end with the release year in parentheses, and MovieLens
    # sorts articles to the end ("Matrix, The").
    clean_title = re.sub(r"\s*\(\d{4}\)\s*$", "", str(title or "")).strip()
    flipped = re.match(r"^(.*),\s*(The|A|An)$", clean_title, flags=re.IGNORECASE)
    if flipped:
        clean_title = f"{flipped.group(2)} {flipped.group(1)}"
    query = f"{clean_title} {year}" if year else clean_title
    return f"{JUSTWATCH_BASE}/{slug}/search?" + urllib.parse.urlencode(
        {"q": query}
    )


def _release_year(value) -> int | None:
    """Extract a year from a TMDB ``release_date`` such as 1999-03-31."""
    match = re.match(r"(\d{4})", str(value or "").strip())
    return int(match.group(1)) if match else None


def _watch_providers(
    payload: dict | None, region: str, title: str, year: int | None
) -> dict:
    """Shape TMDB's ``watch/providers`` payload for the details dialog.

    Returns the offers for one region grouped by how the movie can be
    watched, plus the TMDB watch page (which redirects to JustWatch) and a
    keyless JustWatch search link used when no region data exists.
    """
    results = (payload or {}).get("results") or {}
    entry = results.get(region) or {}

    groups: dict[str, list[dict]] = {}
    for group in ("flatrate", "free", "ads", "rent", "buy"):
        providers = []
        seen = set()
        for item in entry.get(group) or []:
            name = str(item.get("provider_name", "") or "").strip()
            if not name or name.lower() in seen:
                continue
            seen.add(name.lower())
            logo = str(item.get("logo_path", "") or "").strip()
            providers.append(
                {
                    "name": name,
                    "logo_url": f"{WATCH_LOGO_BASE}{logo}" if logo else "",
                }
            )
        if providers:
            groups[group] = providers

    return {
        "region": region,
        "available": bool(groups),
        "link": str(entry.get("link", "") or "").strip(),
        "groups": groups,
        "search_url": _justwatch_search_url(region, title, year),
    }


def _pick_tmdb_video(videos: list[dict]) -> dict | None:
    candidates = [
        video
        for video in videos
        if str(video.get("site", "")).lower() == "youtube"
        and video.get("key")
        and str(video.get("type", "")).lower() in {"trailer", "teaser"}
    ]
    if not candidates:
        return None

    def rank(video: dict) -> tuple:
        return (
            bool(video.get("official")),
            str(video.get("type", "")).lower() == "trailer",
            str(video.get("iso_639_1", "")).lower() == "en",
            int(video.get("size") or 0),
        )

    return max(candidates, key=rank)


def _tmdb_extras(tmdb_id: int | None) -> dict | None:
    if not tmdb_id:
        return None

    key, token = _tmdb_credentials()
    if not key and not token:
        return None

    url = (
        f"https://api.themoviedb.org/3/movie/{int(tmdb_id)}"
        "?append_to_response=credits,videos,watch/providers"
        "&language=en-US"
    )
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    else:
        url += "&" + urllib.parse.urlencode({"api_key": key})

    try:
        data = _get_json(url, headers=headers)
    except Exception:
        return None

    video = _pick_tmdb_video(
        list((data.get("videos") or {}).get("results") or [])
    )
    cast = []
    for person in list((data.get("credits") or {}).get("cast") or [])[:8]:
        name = str(person.get("name", "") or "").strip()
        if not name:
            continue
        profile = str(person.get("profile_path", "") or "").strip()
        cast.append(
            {
                "name": name,
                "character": str(person.get("character", "") or "").strip(),
                "photo_url": f"{TMDB_IMAGE_BASE}{profile}" if profile else "",
            }
        )

    return {
        "cast": cast,
        "overview": str(data.get("overview", "") or "").strip(),
        "trailer": (
            {
                "key": video["key"],
                "name": str(video.get("name", "") or "Trailer").strip(),
            }
            if video
            else None
        ),
        "watch": _watch_providers(
            data.get("watch/providers"),
            _watch_region(),
            str(data.get("title", "") or ""),
            _release_year(data.get("release_date")),
        ),
        "source": "TMDB",
    }


# ---------------------------------------------------------------------------
# YouTube trailer search (keyless fallback)
# ---------------------------------------------------------------------------


def _title_variants(title: str) -> list[str]:
    """Turn a MovieLens title into useful video search phrases."""
    base = re.sub(r"\s*\(\d{4}\)\s*$", "", str(title)).strip()

    alternate = None
    match = re.search(r"\(([^)]+)\)\s*$", base)
    if match and not re.fullmatch(r"\d{4}", match.group(1).strip()):
        alternate = match.group(1).strip()
        base = base[: match.start()].strip()

    def move_article(value: str) -> str:
        article_match = re.match(r"^(.*),\s*(The|A|An)$", value, re.I)
        if article_match:
            return f"{article_match.group(2)} {article_match.group(1)}"
        return value

    variants = [move_article(base)]
    if alternate:
        alternate_variant = move_article(alternate)
        if alternate_variant.lower() not in {
            variant.lower() for variant in variants
        }:
            variants.append(alternate_variant)
    return [variant for variant in variants if variant]


def _normalise(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _extract_video_renderers(data: dict) -> list[dict]:
    found: list[dict] = []
    stack = [data]
    while stack and len(found) < 30:
        node = stack.pop()
        if isinstance(node, dict):
            renderer = node.get("videoRenderer")
            if isinstance(renderer, dict):
                video_id = renderer.get("videoId")
                title_obj = renderer.get("title") or {}
                runs = title_obj.get("runs") or []
                title_text = "".join(
                    str(run.get("text", "")) for run in runs
                ) or str(title_obj.get("simpleText", ""))
                if video_id and title_text:
                    found.append(
                        {"video_id": video_id, "title": title_text}
                    )
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return found


def _youtube_search_api(query: str) -> dict:
    payload = json.dumps(
        {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20240101.00.00",
                    "hl": "en",
                    "gl": "US",
                }
            },
            "query": query,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{YOUTUBE_API_URL}?key={YOUTUBE_WEB_KEY}",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": BROWSER_HEADERS["User-Agent"],
            "Accept-Language": "en-US,en;q=0.9",
            "X-Youtube-Client-Name": "1",
            "X-Youtube-Client-Version": "2.20240101.00.00",
        },
        method="POST",
    )
    with urllib.request.urlopen(
        request, timeout=YOUTUBE_TIMEOUT, context=SSL_CONTEXT
    ) as response:
        return json.loads(
            _read_response(response, YOUTUBE_TOTAL_TIMEOUT)
        )


def _youtube_search(query: str) -> list[dict]:
    global _YOUTUBE_COOLDOWN_UNTIL
    if time.time() < _YOUTUBE_COOLDOWN_UNTIL:
        return []

    # The JSON search endpoint used by YouTube's web client is much less
    # throttled than scraping the results page, so try it first.
    try:
        data = _youtube_search_api(query)
        found = _extract_video_renderers(data)
        if found:
            return found
    except Exception:
        pass

    url = "https://www.youtube.com/results?" + urllib.parse.urlencode(
        {"search_query": query}
    )
    try:
        html = _read(
            url,
            headers=BROWSER_HEADERS,
            timeout=YOUTUBE_TIMEOUT,
            total_timeout=YOUTUBE_TOTAL_TIMEOUT,
        )
    except Exception:
        # If YouTube is unreachable or throttling us, stop retrying for a
        # while so opening more movies stays fast.
        _YOUTUBE_COOLDOWN_UNTIL = time.time() + 10 * 60
        raise

    match = re.search(
        r"var ytInitialData = (\{.*?\});</script>", html, re.S
    )
    if not match:
        return []

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    return _extract_video_renderers(data)


def _bing_video_search(query: str) -> list[dict]:
    """Search Bing Videos and return linked YouTube results.

    The results page is far more permissive than YouTube's own search
    endpoint. Each result card carries a JSON ``mmeta`` attribute with the
    video URL and an ``aria-label`` with the title, so the two are paired
    within one card to avoid mixing titles and IDs.
    """
    url = "https://www.bing.com/videos/search?" + urllib.parse.urlencode(
        {"q": query}
    )
    page = _read(
        url,
        headers=BROWSER_HEADERS,
        timeout=BING_TIMEOUT,
        total_timeout=BING_TOTAL_TIMEOUT,
    )

    found: list[dict] = []
    seen = set()
    for raw_meta, aria_label in _BING_CARD_RE.findall(page):
        try:
            meta = json.loads(html.unescape(raw_meta))
        except json.JSONDecodeError:
            continue
        media_url = str(meta.get("murl", "") or meta.get("pgurl", ""))
        match = re.search(
            r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})",
            media_url,
        )
        if not match:
            continue
        title = re.sub(
            r"\s+from\s+(?:YouTube|Dailymotion|Vimeo).*$",
            "",
            html.unescape(aria_label),
        ).strip()
        video_id = match.group(1)
        if not title or video_id in seen:
            continue
        seen.add(video_id)
        found.append({"video_id": video_id, "title": title})
    return found


def _score_trailer(video_title: str, movie_title: str, year: int | None) -> int:
    video = _normalise(video_title)
    movie = _normalise(movie_title)
    if not video or not movie:
        return -100

    tokens = [
        token
        for token in movie.split()
        if len(token) > 1 and token not in _STOP_WORDS
    ]
    matched = sum(1 for token in tokens if token in video)
    if tokens:
        required = (
            len(tokens)
            if len(tokens) <= 3
            else max(2, math.ceil(len(tokens) * 0.6))
        )
        if matched < required:
            return -100
    if any(word in video for word in _TRAILER_REJECT_WORDS):
        return -100

    score = 0
    if "official trailer" in video:
        score += 8
    elif "trailer" in video:
        score += 5
    if "teaser" in video:
        score += 1
    if year:
        if str(year) in video:
            score += 5
        else:
            score -= 4
    if "official" in video:
        score += 2
    if tokens:
        score += round(6 * matched / len(tokens))

    # A sequel/remake such as "Toy Story 5" must not win a search for the
    # original "Toy Story (1995)".
    if re.search(rf"\b{re.escape(movie)}\s+\d{{1,2}}\b", video):
        score -= 10

    for word in _TRAILER_BAD_WORDS:
        if word in video:
            score -= 10
    for word in ("upscaled", "re upload", "re-upload", "ai trailer"):
        if word in video:
            score -= 3

    other_years = re.findall(r"\b(?:19|20)\d{2}\b", video)
    if year and other_years and str(year) not in other_years:
        score -= 5

    return score


def _find_trailer(title: str, year: int | None) -> dict | None:
    best: dict | None = None
    best_score = -100
    variants = _title_variants(title)[:2]
    queries = []
    for variant in variants:
        if year:
            queries.append((variant, f"{variant} {year} official trailer"))
        else:
            queries.append((variant, f"{variant} official trailer"))
    if year:
        queries.append((variants[0], f"{variants[0]} {year} trailer"))
    else:
        queries.append((variants[0], f"{variants[0]} trailer"))

    bing_returned_results = False
    bing_failed = False
    for variant, query in queries[:3]:
        try:
            videos = _bing_video_search(query)
        except Exception:
            videos = []
            bing_failed = True
        if videos:
            bing_returned_results = True
        for video in videos:
            score = _score_trailer(video["title"], variant, year)
            if score > best_score:
                best = video
                best_score = score
        if best_score >= 6:
            break

    # Bing has results but none of them look like this movie's trailer,
    # which usually means no trailer exists. Avoid a slow YouTube retry for
    # unknown titles and only fall back when Bing itself failed.
    if best_score < 6 and (not bing_returned_results or bing_failed):
        for variant, query in queries[:2]:
            try:
                videos = _youtube_search(query)
            except Exception:
                continue
            for video in videos:
                score = _score_trailer(video["title"], variant, year)
                if score > best_score:
                    best = video
                    best_score = score
            if best_score >= 6:
                break

    if not best or best_score < 6:
        return None
    return {
        "key": best["video_id"],
        "name": best["title"],
        "source": "YouTube",
    }


# ---------------------------------------------------------------------------
# Cast (keyless fallback: Wikidata + Wikipedia)
# ---------------------------------------------------------------------------


def _wikidata_cast(imdb_id: str) -> tuple[str | None, list[dict]]:
    if not imdb_id or not re.fullmatch(r"tt\d{7,10}", imdb_id):
        return None, []

    query = f"""
    SELECT ?actor ?actorLabel ?characterLabel ?article WHERE {{
      ?film wdt:P345 "{imdb_id}".
      OPTIONAL {{
        ?film p:P161 ?statement.
        ?statement ps:P161 ?actor.
        OPTIONAL {{ ?statement pq:P453 ?character. }}
      }}
      OPTIONAL {{
        ?article schema:about ?film;
                 schema:isPartOf <https://en.wikipedia.org/>.
      }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
    }}
    LIMIT 20
    """
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
        {"query": query, "format": "json"}
    )
    try:
        data = _get_json(url, attempts=1)
    except Exception:
        return None, []

    bindings = list((data.get("results") or {}).get("bindings") or [])
    article = None
    cast: list[dict] = []
    seen = set()

    for row in bindings:
        article_url = str(row.get("article", {}).get("value", ""))
        if article and not article_url:
            continue
        if article_url and "wikipedia.org/wiki/" in article_url:
            article = urllib.parse.unquote(
                article_url.rsplit("/wiki/", 1)[-1]
            ).replace("_", " ")

        name = str(row.get("actorLabel", {}).get("value", "")).strip()
        if not name or re.fullmatch(r"Q\d+", name):
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        character = str(
            row.get("characterLabel", {}).get("value", "")
        ).strip()
        if re.fullmatch(r"Q\d+", character):
            character = ""
        cast.append(
            {
                "name": name,
                "character": character,
                "photo_url": "",
            }
        )

    return article, cast


def _wikipedia_search(title: str, year: int | None) -> str | None:
    clean_title = _title_variants(title)[0]
    search = f'{clean_title} {year} film' if year else f"{clean_title} film"
    try:
        data = _wiki_api(
            {
                "action": "query",
                "list": "search",
                "srsearch": search,
                "format": "json",
                "formatversion": "2",
                "srlimit": "5",
            }
        )
    except Exception:
        return None

    hits = list((data.get("query") or {}).get("search") or [])
    if not hits:
        return None

    expected = _normalise(clean_title)
    best_hit = None
    best_score = -100
    for hit in hits:
        hit_title = str(hit.get("title", ""))
        normalised = _normalise(hit_title)
        score = 0
        if normalised == expected:
            score += 10
        elif normalised.startswith(expected + " ") or (
            expected + " film" in normalised
        ):
            score += 6
        elif expected in normalised:
            score += 3
        if year and str(year) in normalised:
            score += 3
        if normalised.startswith("list of"):
            score -= 15
        if score > best_score:
            best_hit = hit_title
            best_score = score

    if best_score < 6:
        return None
    return best_hit


def _clean_role(role: str) -> str:
    role = re.sub(r"\[\s*\d+\s*\]", "", role)
    role = re.sub(r"\s+", " ", role).strip(" .,;:")
    role = re.sub(r"\s+([,.;:])", r"\1", role)
    # Keep the character name, drop plot descriptions after a comma,
    # semicolon, or parenthetical note.
    role = re.split(r"\s*[,;(]\s*", role, maxsplit=1)[0].strip(" .,;:")
    if len(role) > 70:
        role = role[:67].rsplit(" ", 1)[0] + "…"
    return role


def _wikipedia_cast(article: str | None) -> list[dict]:
    if not article:
        return []

    try:
        data = _wiki_api(
            {
                "action": "parse",
                "page": article,
                "prop": "text",
                "format": "json",
                "formatversion": "2",
                "redirects": "1",
            }
        )
    except Exception:
        return []

    html = str((data.get("parse") or {}).get("text", ""))
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    heading = None
    for candidate in soup.find_all(["h2", "h3"]):
        heading_text = candidate.get_text(" ", strip=True)
        if re.search(r"\b(cast|starring|casting)\b", heading_text, re.I):
            heading = candidate
            break
    if heading is None:
        return []

    # MediaWiki wraps headings in <div class="mw-heading">, so the section
    # content is a sibling of that wrapper, not of the <h2>/<h3> itself.
    section_start = heading
    parent = heading.parent
    if parent is not None and parent.name == "div":
        classes = parent.get("class") or []
        if "mw-heading" in classes:
            section_start = parent

    def is_heading(node) -> bool:
        if node.name in {"h2", "h3"}:
            return True
        if node.name == "div" and "mw-heading" in (node.get("class") or []):
            return node.find(["h2", "h3"]) is not None
        return False

    items = []
    table_rows = []
    for sibling in section_start.find_next_siblings():
        if is_heading(sibling):
            break
        if sibling.name in {"ul", "ol"}:
            items.extend(sibling.find_all("li"))
        elif sibling.name == "div":
            items.extend(sibling.find_all("li"))
        elif sibling.name == "table":
            for row in sibling.find_all("tr"):
                cells = row.find_all(["td", "th"], recursive=False)
                if len(cells) >= 2:
                    table_rows.append((cells[0], cells[1]))

    cast: list[dict] = []
    seen = set()

    def add_person(name: str, role: str) -> None:
        name = re.sub(r"\[\s*\d+\s*\]", "", name)
        name = re.sub(r"\s+", " ", name).strip(" .,;:")
        name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
        role = _clean_role(role)
        if not name or len(name) > 70:
            return
        if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ' .\-]+", name):
            return
        key = name.lower()
        if key in seen:
            return
        seen.add(key)
        cast.append(
            {"name": name, "character": role, "photo_url": ""}
        )

    for first_cell, second_cell in table_rows:
        name = first_cell.get_text(" ", strip=True)
        role = second_cell.get_text(" ", strip=True)
        if name.lower() in {"actor", "actress", "cast member"}:
            continue
        add_person(name, role)
        if len(cast) >= 8:
            break

    for item in items:
        # Drop nested lists from a copy so an outer item such as
        # "John Cusack as Rob Gordon <ul><li>Drake Bell ...</li></ul>"
        # does not merge two actors into one row.
        item_copy = BeautifulSoup(str(item), "html.parser")
        for nested in item_copy.find_all(["ul", "ol"]):
            nested.decompose()
        text = item_copy.get_text(" ", strip=True)
        text = re.sub(r"\[\s*\d+\s*\]", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        if not text or re.match(
            r"^(see also|main article|further information|the film stars)",
            text,
            re.I,
        ):
            continue

        parts = re.split(
            r"\s+(?:as|–|—|-)\s+", text, maxsplit=1, flags=re.I
        )
        if len(parts) < 2:
            continue

        add_person(parts[0], parts[1])
        if len(cast) >= 8:
            break

    return cast


def _attach_photos(cast: list[dict]) -> list[dict]:
    names = [person["name"] for person in cast if person.get("name")]
    if not names:
        return cast

    by_name: dict[str, str] = {}
    try:
        data = _wiki_api(
            {
                "action": "query",
                "titles": "|".join(names[:20]),
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": "240",
                "format": "json",
                "formatversion": "2",
                "redirects": "1",
            }
        )
    except Exception:
        return cast

    query = data.get("query") or {}
    title_map: dict[str, str] = {}
    for item in query.get("normalized") or []:
        title_map[str(item.get("from", ""))] = str(item.get("to", ""))
    for item in query.get("redirects") or []:
        title_map[str(item.get("from", ""))] = str(item.get("to", ""))

    pages = {}
    for page in query.get("pages") or []:
        pages[str(page.get("title", ""))] = page

    for name in names:
        resolved = name
        seen_titles = set()
        while resolved in title_map and resolved not in seen_titles:
            seen_titles.add(resolved)
            resolved = title_map[resolved]
        page = pages.get(resolved) or pages.get(name)
        thumbnail = str(
            ((page or {}).get("thumbnail") or {}).get("source", "")
        ).strip()
        lower_thumbnail = thumbnail.lower()
        if (
            thumbnail.startswith(("https://", "http://"))
            and "signature" not in lower_thumbnail
            and not lower_thumbnail.split("?")[0].endswith(".svg")
        ):
            by_name[name] = thumbnail

    for person in cast:
        person["photo_url"] = by_name.get(person["name"], "")
    return cast


def _wikipedia_description(article: str | None) -> str:
    """Short plot description from Wikipedia's page summary endpoint."""
    if not article:
        return ""
    slug = urllib.parse.quote(str(article).replace(" ", "_"), safe="")
    try:
        data = _get_json(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}",
            attempts=1,
        )
    except Exception:
        return ""
    extract = str(data.get("extract", "") or "").strip()
    extract = re.sub(r"\s+", " ", extract)
    if len(extract) > 700:
        extract = extract[:697].rsplit(" ", 1)[0] + "…"
    return extract


def _web_description(
    title: str, year: int | None, imdb_id: str
) -> str:
    article, _ = _wikidata_cast(imdb_id)
    if not article:
        article = _wikipedia_search(title, year)
    return _wikipedia_description(article)


def _web_cast(
    title: str, year: int | None, imdb_id: str
) -> list[dict]:
    article, wikidata_cast = _wikidata_cast(imdb_id)
    if not article:
        article = _wikipedia_search(title, year)

    wikipedia_cast = _wikipedia_cast(article)
    cast = wikipedia_cast or wikidata_cast
    return _attach_photos(cast[:8])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _web_extras(
    title: str, year: int | None, imdb_id: str
) -> dict:
    executor = ThreadPoolExecutor(max_workers=3)
    cast_future = executor.submit(_web_cast, title, year, imdb_id)
    trailer_future = executor.submit(_find_trailer, title, year)
    description_future = executor.submit(
        _web_description, title, year, imdb_id
    )
    deadline = time.monotonic() + 25

    try:
        cast = cast_future.result(
            timeout=max(0.1, deadline - time.monotonic())
        )
    except Exception:
        cast = []
    try:
        trailer = trailer_future.result(
            timeout=max(0.1, deadline - time.monotonic())
        )
    except Exception:
        trailer = None
    try:
        overview = description_future.result(
            timeout=max(0.1, deadline - time.monotonic())
        )
    except Exception:
        overview = ""
    finally:
        # Never block the dialog on a slow background request.
        executor.shutdown(wait=False)

    return {
        "cast": cast,
        "overview": overview,
        "trailer": trailer,
        "watch": None,
        "source": "web",
    }


def _normalise_imdb_id(imdb_id) -> str:
    value = str(imdb_id or "").strip()
    if not value or value.lower() in {"nan", "none", "<na>"}:
        return ""
    if value.isdigit():
        return "tt" + value.zfill(7)
    if value.lower().startswith("tt"):
        return value.lower()
    return ""


@st.cache_data(ttl=6 * 60 * 60, show_spinner=False)
def get_movie_extras(
    tmdb_id: int | None, imdb_id: str, title: str, year: int | None
) -> dict:
    """Return ``{"cast", "overview", "trailer", "watch", "source"}``.

    TMDB is tried first when credentials are configured. Missing pieces are
    filled from the keyless web fallback.

    ``watch`` is always a dict shaped by ``_watch_providers()``, so the UI can
    render a search fallback even when no TMDB credentials exist.
    """
    tmdb_extras = _tmdb_extras(tmdb_id)
    web_extras = None

    if (
        not tmdb_extras
        or not tmdb_extras.get("cast")
        or not tmdb_extras.get("trailer")
        or not tmdb_extras.get("overview")
    ):
        try:
            web_extras = _web_extras(
                title, year, _normalise_imdb_id(imdb_id)
            )
        except Exception:
            web_extras = {
                "cast": [],
                "overview": "",
                "trailer": None,
                "source": "web",
            }

    if tmdb_extras:
        if not tmdb_extras.get("cast") and web_extras:
            tmdb_extras["cast"] = web_extras["cast"]
        if not tmdb_extras.get("trailer") and web_extras:
            tmdb_extras["trailer"] = web_extras["trailer"]
        if not tmdb_extras.get("overview") and web_extras:
            tmdb_extras["overview"] = web_extras.get("overview", "")
        tmdb_extras.setdefault(
            "watch", _watch_providers(None, _watch_region(), title, year)
        )
        return tmdb_extras

    extras = web_extras or {
        "cast": [],
        "overview": "",
        "trailer": None,
        "source": "none",
    }
    extras["watch"] = _watch_providers(None, _watch_region(), title, year)
    return extras
