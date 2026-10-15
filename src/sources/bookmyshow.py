import json
import logging
import os
import random
import time

from bs4 import BeautifulSoup

from src.common import bookmyshow
from src.processors.geo import BLR_LAT, BLR_LNG, MAX_DISTANCE_KM
from src.processors.geo import extract_coords, haversine_distance

LISTING = "https://in.bookmyshow.com/api/explore/v1/discover/{}-bengaluru"
CATEGORIES = ("events", "plays", "activities")
# The mobile web app code is the only one that returns the paginated listing
HEADERS = {
    "x-app-code": "WEBV2",
    "x-platform-code": "MOBILE-WEB",
    "x-region-code": "BANG",
    "x-region-slug": "bengaluru",
}
MAX_PAGES = 150


def listing_page(category, scroll_id, page_id, bms_id):
    params = {"region": "BANG", "embedded": "true"}
    if scroll_id:
        params |= {"scrollId": scroll_id, "pageId": page_id}
    headers = HEADERS | {
        "x-bms-id": bms_id,
        "referer": f"https://in.bookmyshow.com/explore/{category}-bengaluru",
    }
    response = bookmyshow.fetcher().get(
        url=LISTING.format(category), params=params, headers=headers, cache=False
    )
    response.raise_for_status()
    return response.json()


def listing():
    bms_id = f"1.{random.randrange(10**8)}.{int(time.time() * 1000)}"
    events, first = {}, True
    for category in CATEGORIES:
        scroll_id = None
        for page_id in range(1, MAX_PAGES + 1):
            if not first:
                bookmyshow.pause()
            first = False
            data = listing_page(category, scroll_id, page_id, bms_id)
            schema = (data.get("meta") or {}).get("ldSchema", {}).get("eventsSchema") or []
            fresh = [e for e in schema if e.get("url") and e["url"] not in events]
            events |= {e["url"]: e for e in fresh}
            logging.info("BMS %s page %s: %s new events", category, page_id, len(fresh))
            scroll_id = data.get("scrollId")
            if not scroll_id or not fresh:
                break
    return list(events.values())


def in_bengaluru(event):
    lat, lng = extract_coords(event)
    if lat is not None:
        return haversine_distance(lat, lng, BLR_LAT, BLR_LNG) <= MAX_DISTANCE_KM
    place = json.dumps(event.get("location") or "").lower()
    return "bengaluru" in place or "bangalore" in place


def page_events(summary):
    html = bookmyshow.page(summary["url"])
    if not html:
        return []
    about = bookmyshow.synopsis(html)
    found = []
    for event in bookmyshow.jsonld_events(BeautifulSoup(html, "html.parser")):
        if not in_bengaluru(event):
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
    budget = int(os.getenv("BMS_MAX_FETCHES", "150"))
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
