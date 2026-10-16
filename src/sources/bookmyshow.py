import json
import logging
import os
import random
import tempfile
import time

from bs4 import BeautifulSoup

from src.common import bookmyshow

LISTING = "https://in.bookmyshow.com/api/explore/v1/discover/{}-bengaluru"
# The mobile web app code is the only one that returns the paginated listing
HEADERS = {
    "x-app-code": "WEBV2",
    "x-platform-code": "MOBILE-WEB",
    "x-region-code": "BANG",
    "x-region-slug": "bengaluru",
}
# One listing stops after about 111 pages, so list each event category on its own
CATEGORIES = (
    "music-shows", "comedy-shows", "performances", "kids", "meetups", "talks",
    "exhibitions", "screening", "spirituality", "conferences", "award-shows", "nye-parties",
)
MAX_PAGES = 150
# Workshops and activities are mostly the same catalogue at every outlet
SOONEST_PAGES = 30
LISTINGS = (
    *(("events", c, MAX_PAGES) for c in CATEGORIES),
    ("plays", None, MAX_PAGES),
    ("events", "workshops", SOONEST_PAGES),
    ("activities", None, SOONEST_PAGES),
)
# A separate job lists BMS and fills the page cache, the build reads both
MAX_AGE = 2 * 24 * 3600
SUMMARY = {"@type", "name", "url", "startDate", "endDate", "image", "location", "eventStatus"}


def listing_page(path, category, scroll_id, page_id, bms_id):
    params = {"region": "BANG", "embedded": "true", "sortBy": "earliestEventFirst"}
    if category:
        params["categories"] = category
    if scroll_id:
        params |= {"scrollId": scroll_id, "pageId": page_id}
    headers = HEADERS | {
        "x-bms-id": bms_id,
        "referer": f"https://in.bookmyshow.com/explore/{path}-bengaluru",
    }
    response = bookmyshow.fetcher().get(
        url=LISTING.format(path), params=params, headers=headers, cache=False
    )
    response.raise_for_status()
    return response.json()


def walk():
    bms_id = f"1.{random.randrange(10**8)}.{int(time.time() * 1000)}"
    events, first = {}, True
    for path, category, pages in LISTINGS:
        scroll_id = None
        for page_id in range(1, pages + 1):
            if not first:
                bookmyshow.pause()
            first = False
            try:
                data = listing_page(path, category, scroll_id, page_id, bms_id)
            except (OSError, ValueError) as e:
                logging.warning("BMS %s %s page %s failed: %s", path, category, page_id, e)
                break
            schema = (data.get("meta") or {}).get("ldSchema", {}).get("eventsSchema") or []
            fresh = [e for e in schema if e.get("url") and e["url"] not in events]
            events |= {e["url"]: e for e in fresh}
            logging.info("BMS %s %s page %s: %s new events", path, category, page_id, len(fresh))
            scroll_id = data.get("scrollId")
            if not scroll_id or not schema:
                break
    return list(events.values())


def save(path, found):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"listed": time.time(), "events": found}, f)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def clean(summary):
    # Another job wrote this file, so keep only BMS event pages and plain fields
    if not isinstance(summary, dict) or not isinstance(summary.get("url"), str):
        return None
    if not bookmyshow.EVENT_PAGE.match(summary["url"]):
        return None
    return {k: v for k, v in summary.items() if k in SUMMARY and isinstance(v, (str, dict))}


def saved(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    age = time.time() - float(data["listed"])
    if not 0 <= age <= MAX_AGE:
        raise RuntimeError(f"BookMyShow listing at {path} is {age / 3600:.0f}h old")
    return [s for s in map(clean, data["events"]) if s]


def listing():
    path = os.getenv("BMS_LISTING")
    if path and not os.getenv("BMS_CRAWL"):
        return saved(path)
    found = walk()
    if path and found:
        save(path, found)
    return found


def page_events(summary):
    html = bookmyshow.page(summary["url"])
    if not html:
        return []
    about = bookmyshow.synopsis(html)
    found = []
    for event in bookmyshow.jsonld_events(BeautifulSoup(html, "html.parser")):
        if not bookmyshow.in_bengaluru(event):
            continue
        result = summary | event
        result.pop("@context", None)
        # BMS names itself as the organizer of every event
        if (result.get("organizer") or {}).get("name") == "BookMyShow":
            del result["organizer"]
        if about:
            result["description"] = about
        found.append(result)
    return found


def events():
    found = sorted(listing(), key=lambda e: str(e.get("startDate")))
    # Builds that read a saved listing only use cached pages
    reading = os.getenv("BMS_LISTING") and not os.getenv("BMS_CRAWL")
    budget = int(os.getenv("BMS_MAX_FETCHES", "0" if reading else "150"))
    result, skipped, read = [], 0, 0
    for summary in found:
        if not bookmyshow.cached(summary["url"]):
            if budget <= 0:
                skipped += 1
                continue
            budget -= 1
        page = page_events(summary)
        read += bool(page)
        result += page
    logging.info(
        "BMS: %s listed, %s pages with Bengaluru events, %s events, %s left for later runs",
        len(found), read, len(result), skipped,
    )
    if found and not result:
        raise RuntimeError("No BookMyShow event page could be read")
    return result
