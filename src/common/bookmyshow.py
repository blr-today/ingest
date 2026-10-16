import json
import logging
import random
import re
import time

from bs4 import BeautifulSoup
from urllib.parse import urlparse

from requests.models import PreparedRequest

from .fetch import Fetch

EVENT_PAGE = re.compile(r"^https://in\.bookmyshow\.com/(plays|events|activities)/[^/]+/\w+")
STATE_MARKER = "window.__INITIAL_STATE__ = "
FIELDS = ("image", "offers", "performer", "typicalAgeRange", "inLanguage", "duration")
_fetcher = None


def fetcher():
    global _fetcher
    _fetcher = _fetcher or Fetch(cache={"days": 3}, browser="chrome150")
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


def jsonld_event(soup):
    return next(jsonld_events(soup), {})


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


def parse(html):
    event = jsonld_event(BeautifulSoup(html, "html.parser"))
    details = {k: event[k] for k in FIELDS if event.get(k)}
    if about := synopsis(html):
        details["description"] = about
    return details


def pause():
    # The /bot page promises at least 10 seconds between page loads per host
    time.sleep(random.uniform(10, 15))


def empty(url, html):
    # Under load BMS serves the app shell without the event data
    return f'"{urlparse(url).path}":{{"status":"uninitialized"' in html


def cache_key(url):
    request = PreparedRequest()
    request.prepare(method="GET", url=url)
    return fetcher().cache.create_key(request)


def cached(url):
    response = fetcher().cache.get_response(cache_key(url))
    return response is not None and not response.is_expired and not empty(url, response.text)


def page(url, tries=2):
    for _ in range(tries):
        try:
            response = fetcher().get(url=url)
        except OSError as e:
            logging.warning("BookMyShow failed for %s: %s", url, e)
            pause()
            continue
        if not getattr(response, "from_cache", False):
            pause()
        if response.status_code != 200:
            logging.warning("BookMyShow returned %s for %s", response.status_code, url)
            return None
        if not empty(url, response.text):
            return response.text
        fetcher().cache.delete(cache_key(url))
    logging.warning("BookMyShow gave no event data for %s", url)
    return None


def details(url):
    html = page(url)
    return parse(html) if html else {}
