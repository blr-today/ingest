import json
import sqlite3
from functools import cache

from .base import Processor
from .cost import as_keywords, flatten

LIMIT = 8


def count(value):
    if isinstance(value, dict):
        value = value.get("value")
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def tickets_left(event):
    left = count(event.get("remainingAttendeeCapacity"))
    if left is not None:
        return left
    offers = list(flatten(event.get("offers")))
    if not offers:
        return None
    total = 0
    for offer in offers:
        n = count(offer.get("remainingAttendeeCapacity", offer.get("inventoryLevel")))
        if n is None and "SoldOut" not in str(offer.get("availability")):
            return None
        total += n or 0
    return total


def listing(url):
    return url.split("#")[0]


@cache
def slot_totals(db="events.db"):
    # Slots of one listing share a url, and one uncounted slot hides the total
    totals = {}
    try:
        rows = sqlite3.connect(f"file:{db}?mode=ro", uri=True).execute(
            "SELECT url, event_json FROM events"
        )
        for url, event_json in rows:
            left = tickets_left(json.loads(event_json))
            key = listing(url)
            if key in totals and totals[key] is None:
                continue
            totals[key] = None if left is None else totals.get(key, 0) + left
    except sqlite3.Error:
        return {}
    return totals


class LastCall(Processor):
    PRIORITY = 900

    @staticmethod
    def process(url, event):
        left = slot_totals().get(listing(url), tickets_left(event))
        keywords = as_keywords(event.get("keywords"))
        if left is not None and 0 < left <= LIMIT and "LASTCALL" not in keywords:
            event["keywords"] = keywords + ["LASTCALL"]
        return event
