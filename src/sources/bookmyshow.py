import logging
import os
import random
import time

from bs4 import BeautifulSoup

from src.common import bookmyshow

LISTING = "https://in.bookmyshow.com/api/explore/v1/discover/events-bengaluru"
# The mobile web app code is the only one that returns the paginated listing
HEADERS = {
    "x-app-code": "WEBV2",
    "x-platform-code": "MOBILE-WEB",
    "x-region-code": "BANG",
    "x-region-slug": "bengaluru",
    "referer": "https://in.bookmyshow.com/explore/events-bengaluru",
}
MAX_PAGES = 150


def listing_page(scroll_id, page_id, bms_id):
    params = {"region": "BANG", "embedded": "true"}
    if scroll_id:
        params |= {"scrollId": scroll_id, "pageId": page_id}
    response = bookmyshow.fetcher().get(
        url=LISTING, params=params, headers=HEADERS | {"x-bms-id": bms_id}, cache=False
    )
    response.raise_for_status()
    return response.json()


def listing():
    bms_id = f"1.{random.randrange(10**8)}.{int(time.time() * 1000)}"
    events, scroll_id = {}, None
    for page_id in range(1, MAX_PAGES + 1):
        if page_id > 1:
            bookmyshow.pause()
        data = listing_page(scroll_id, page_id, bms_id)
        schema = (data.get("meta") or {}).get("ldSchema", {}).get("eventsSchema") or []
        fresh = [e for e in schema if e.get("url") and e["url"] not in events]
        events |= {e["url"]: e for e in fresh}
        logging.info("BMS listing page %s: %s new events", page_id, len(fresh))
        scroll_id = data.get("scrollId")
        if not scroll_id or not fresh:
            break
    return list(events.values())


def page_event(html):
    event = bookmyshow.jsonld_event(BeautifulSoup(html, "html.parser"))
    if event and (about := bookmyshow.synopsis(html)):
        event["description"] = about
    return event


def event(summary):
    html = bookmyshow.page(summary["url"])
    full = page_event(html) if html else {}
    if not full:
        return None
    result = summary | full
    result.pop("@context", None)
    # BMS names itself as the organizer of every event
    if (result.get("organizer") or {}).get("name") == "BookMyShow":
        del result["organizer"]
    return result


def events():
    found = sorted(listing(), key=lambda e: str(e.get("startDate")))
    budget = int(os.getenv("BMS_MAX_FETCHES", "150"))
    result, skipped = [], 0
    for summary in found:
        if not bookmyshow.cached(summary["url"]):
            if budget <= 0:
                skipped += 1
                continue
            budget -= 1
        if full := event(summary):
            result.append(full)
    logging.info("BMS: %s listed, %s kept, %s left for later runs", len(found), len(result), skipped)
    if found and not result:
        raise RuntimeError("No BookMyShow event page could be read")
    return result
