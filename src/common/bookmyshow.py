import datetime
import glob
import json
import logging
import os
import random
import re
import tempfile
import time
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from src.processors.geo import (
    BLR_LAT,
    BLR_LNG,
    MAX_DISTANCE_KM,
    extract_coords,
    haversine_distance,
)

from .fetch import Fetch
from .tz import IST

EVENT_PAGE = re.compile(r"^https://in\.bookmyshow\.com/(plays|events|activities)/[^/]+/\w+")
STATE_MARKER = "window.__INITIAL_STATE__ = "
FIELDS = ("image", "offers", "performer", "typicalAgeRange", "inLanguage", "duration")
# Each page is one file named for its soonest show, so past shows are easy to clear
VERSION = 1
DAY = 24 * 3600
PRUNE = 7 * DAY
UNDATED = "9999-12-31"
_fetcher = None


def fetcher():
    global _fetcher
    _fetcher = _fetcher or Fetch(browser="chrome150")
    return _fetcher


def jsonld_events(soup):
    # Pages of multi-city events list one event per venue
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "null")
        except json.JSONDecodeError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and str(item.get("@type", "")).endswith("Event"):
                yield item


def in_bengaluru(event):
    lat, lng = extract_coords(event)
    if lat is not None:
        return haversine_distance(lat, lng, BLR_LAT, BLR_LNG) <= MAX_DISTANCE_KM
    place = json.dumps(event.get("location") or "").lower()
    return "bengaluru" in place or "bangalore" in place


def bengaluru_first(events):
    # Touring shows list other cities first, so prefer the Bengaluru show
    return next((e for e in events if in_bengaluru(e)), events[0] if events else {})


def synopsis(html):
    if STATE_MARKER not in html:
        return None
    start = html.index(STATE_MARKER) + len(STATE_MARKER)
    try:
        state, _ = json.JSONDecoder().raw_decode(html[start:])
    except json.JSONDecodeError:
        return None
    queries = state.get("eventsSynopsisApi", {}).get("queries", {})
    widgets = next(
        (q["data"]["widgets"] for q in queries.values() if "widgets" in (q.get("data") or {})),
        {},
    )
    about = "".join(
        t.get("text", "")
        for card in widgets.get("ABOUT_THE_EVENT", {}).get("cards", [])
        for t in card.get("text") or []
        if isinstance(t, dict)
    )
    text = BeautifulSoup(about, "html.parser").get_text("\n").strip()
    return re.sub(r"\n{3,}", "\n\n", text) or None


def record(url, html):
    events = list(jsonld_events(BeautifulSoup(html, "html.parser")))
    return {"version": VERSION, "url": url, "fetched": time.time(), "events": events, "synopsis": synopsis(html)}


def summarize(data):
    event = bengaluru_first(data["events"])
    details = {k: event[k] for k in FIELDS if event.get(k)}
    if data.get("synopsis"):
        details["description"] = data["synopsis"]
    return details


def parse(html):
    return summarize(record(None, html))


def pause():
    # The /bot page promises at least 10 seconds between page loads per host
    time.sleep(random.uniform(10, 15))


def empty(url, html):
    # Under load BMS serves the app shell without the event data
    return f'"{urlparse(url).path}":{{"status":"uninitialized"' in html


def cache_dir():
    return os.path.expanduser(os.getenv("BMS_CACHE", "~/.cache/bms"))


def today():
    return datetime.datetime.now(IST).date().isoformat()


def files(url):
    code = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    if not re.fullmatch(r"\w+", code):
        return []
    return glob.glob(os.path.join(cache_dir(), f"????-??-??-{code}.json"))


def stored(url):
    for path in sorted(files(url), reverse=True):
        if os.path.basename(path)[:10] < today():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if data["version"] == VERSION and isinstance(data["events"], list):
                return data | {"day": os.path.basename(path)[:10]}
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None


def cached(url):
    return stored(url) is not None


def max_age(day):
    # Refresh soon shows more often to catch sell-outs, reschedules and cancellations
    if day == UNDATED:
        return 4 * DAY
    days = (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(today())).days
    return DAY // 2 if days <= 1 else 2 * DAY if days <= 7 else 4 * DAY


def due(url):
    data = stored(url)
    return data is None or time.time() - float(data["fetched"]) > max_age(data["day"])


def soonest(data):
    days = [str(e.get("startDate", ""))[:10] for e in data["events"] if in_bengaluru(e)]
    days = [d for d in days if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and d >= today()]
    return min(days, default=UNDATED)


def save(url, data):
    old = files(url)
    os.makedirs(cache_dir(), exist_ok=True)
    code = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1]
    path = os.path.join(cache_dir(), f"{soonest(data)}-{code}.json")
    fd, tmp = tempfile.mkstemp(dir=cache_dir(), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({k: v for k, v in data.items() if k != "day"}, f, ensure_ascii=False)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
    for other in old:
        if other != path:
            os.unlink(other)


def prune():
    # Drop pages whose soonest show has passed, and pages no longer listed
    removed = 0
    for path in glob.glob(os.path.join(cache_dir(), "????-??-??-*.json")):
        if os.path.basename(path)[:10] < today() or time.time() - os.path.getmtime(path) > PRUNE:
            os.unlink(path)
            removed += 1
    return removed


def page(url, tries=2):
    for _ in range(tries):
        try:
            response = fetcher().get(url=url, cache=False)
        except OSError as e:
            logging.warning("BookMyShow failed for %s: %s", url, e)
            pause()
            continue
        pause()
        if response.status_code != 200:
            logging.warning("BookMyShow returned %s for %s", response.status_code, url)
            return None
        if not empty(url, response.text):
            return response.text
    logging.warning("BookMyShow gave no event data for %s", url)
    return None


def load(url, refresh=False):
    data = stored(url)
    if data and not (refresh and due(url)):
        return data
    html = page(url)
    if not html:
        # Keep the older copy when a refresh fails
        return data
    data = record(url, html)
    save(url, data)
    return data


def details(url):
    data = load(url)
    return summarize(data) if data else {}
