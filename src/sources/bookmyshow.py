import json
import logging
import os
import random
import tempfile
import time

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


def listing_path():
    return os.path.join(bookmyshow.cache_dir(), "listing.json")


def save(found):
    os.makedirs(bookmyshow.cache_dir(), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=bookmyshow.cache_dir(), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"listed": time.time(), "events": found}, f)
        os.replace(tmp, listing_path())
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


def saved():
    path = listing_path()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    age = time.time() - float(data["listed"])
    if not 0 <= age <= MAX_AGE:
        raise RuntimeError(f"BookMyShow listing at {path} is {age / 3600:.0f}h old")
    return [s for s in map(clean, data["events"]) if s]


def crawling():
    return bool(os.getenv("BMS_CRAWL"))


def listing():
    if not crawling():
        return saved()
    found = walk()
    if found:
        save(found)
    return found


def page_events(summary, refresh=False):
    data = bookmyshow.load(summary["url"], refresh)
    if not data:
        return []
    about = data.get("synopsis")
    found = []
    for event in data["events"]:
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
    if crawling():
        logging.info("BMS: cleared %s past or unlisted pages", bookmyshow.prune())
    found = sorted(listing(), key=lambda e: str(e.get("startDate")))
    # Builds that read a saved listing only use cached pages
    budget = int(os.getenv("BMS_MAX_FETCHES", "150" if crawling() else "0"))
    # New pages first, then refresh the soonest shows that are due
    new = [s["url"] for s in found if not bookmyshow.cached(s["url"])]
    stale = [s["url"] for s in found if s["url"] not in new and bookmyshow.due(s["url"])]
    fetch = set((new + stale)[:budget])
    result, read = [], 0
    for summary in found:
        if summary["url"] not in fetch and summary["url"] in new:
            continue
        page = page_events(summary, refresh=summary["url"] in fetch)
        read += bool(page)
        result += page
    logging.info(
        "BMS: %s listed, %s fetched, %s pages with Bengaluru events, %s events, %s new and %s stale left",
        len(found), len(fetch), read, len(result),
        len(set(new) - fetch), len(set(stale) - fetch),
    )
    if found and not result:
        raise RuntimeError("No BookMyShow event page could be read")
    return result
