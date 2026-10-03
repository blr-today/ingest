import json
import math
import sqlite3
from functools import cache

from .base import Processor
from .cost import as_keywords, flatten

LIMIT = 8
SHARE = 0.1


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
        # Sources mark a slot sold out once booking closes, even with seats unsold
        if "SoldOut" in str(offer.get("availability")):
            continue
        n = count(offer.get("remainingAttendeeCapacity", offer.get("inventoryLevel")))
        if n is None:
            return None
        total += n
    return total


def capacity(event):
    return count(event.get("maximumAttendeeCapacity"))


def threshold(total):
    return math.ceil(total * SHARE) if total else LIMIT


def add(a, b):
    return None if a is None or b is None else a + b


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
            event = json.loads(event_json)
            left, seats = totals.get(listing(url), (0, 0))
            totals[listing(url)] = (add(left, tickets_left(event)), add(seats, capacity(event)))
    except sqlite3.Error:
        return {}
    return totals


class LastCall(Processor):
    PRIORITY = 900

    @staticmethod
    def process(url, event):
        left, seats = slot_totals().get(listing(url), (tickets_left(event), capacity(event)))
        keywords = as_keywords(event.get("keywords"))
        if left is not None and 0 < left <= threshold(seats) and "LASTCALL" not in keywords:
            event["keywords"] = keywords + ["LASTCALL"]
        return event
