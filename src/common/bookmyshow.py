import json
import logging
import re
import time

from bs4 import BeautifulSoup

from .fetch import Fetch

# Event page parser, reusable when BMS becomes a proper source (see the bms branch)
EVENT_PAGE = re.compile(r"^https://in\.bookmyshow\.com/(plays|events|activities)/[^/]+/\w+")
STATE_MARKER = "window.__INITIAL_STATE__ = "
FIELDS = ("image", "offers", "performer", "typicalAgeRange", "inLanguage", "duration")
_fetcher = None


def fetcher():
    global _fetcher
    _fetcher = _fetcher or Fetch(browser="chrome")
    return _fetcher


def jsonld_event(soup):
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "null")
        except json.JSONDecodeError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict) and str(item.get("@type", "")).endswith("Event"):
                return item
    return {}


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


def details(url):
    response = fetcher().get(url=url)
    if not getattr(response, "from_cache", False):
        # The /bot page promises 10 seconds between page loads per host
        time.sleep(10)
    if response.status_code != 200:
        logging.warning("BookMyShow returned %s for %s", response.status_code, url)
        return {}
    return parse(response.text)
