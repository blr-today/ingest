from urllib.parse import urlparse, parse_qs
import json
import sys
import uuid
from ..common.fetch import Fetch
from ..jsonnet import transform

BROWSER_CODE = "safari260_ios"
BASE_URL = "https://www.skillboxes.com/servers"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; blr.today-bot; +https://blr.today/bot/)",
}

SKILLBOX_DEBUG_LIMIT = None
CITIES = ("9", "1105542")

fetcher = Fetch(
    cache={
        "days": 1,
        "allowable_codes": (200,),
        "allowable_methods": ["POST"],
    },
    browser=BROWSER_CODE,
)


def get_events(city, page=1):
    payload = {
        "default_city": city,
        "city": city,
        "opcode": "search",
        "type": "fetchAll",
        "eventCityEnb": False,
        "page": page,
    }

    res = fetcher.post(
        url="https://www.skillboxes.com/servers/v3/api/event-new/get-event",
        json=payload,
        headers=HEADERS,
        cache=False,
    )

    if res.status_code != 200:
        raise RuntimeError(f"Failed to get list of events: HTTP {res.status_code}")
    data = res.json()
    for item in data["items"]:
        yield item["slug"]
    if data["next"]:
        yield from get_events(city, page + 1)


def get_event_details(slug):
    payload = {"slug": slug}
    res = fetcher.post(
        url="https://www.skillboxes.com/servers/v3/api/event-new/event-details",
        json=payload,
        headers=HEADERS,
    )

    if res.status_code != 200:
        print(f"[SKILLBOXES] Failed to get details for event {slug}.", file=sys.stderr)
        return None

    return res.json()["data"]


def get_event_tickets(slug):
    try:
        payload = {"slug": slug}
        res = fetcher.post(
            url="https://www.skillboxes.com/servers/v3/api/event-new/event-tickets",
            json=payload,
            headers=HEADERS,
        )

        data = res.json()
        if data["success"] == False:
            return []

        return data["data"]
    except Exception as e:
        if "more than 100 headers" in str(e):
            return []
        else:
            print(
                f"[SKILLBOXES] Error fetching tickets for event {slug}: {e}",
                file=sys.stderr,
            )
            return []


def fetch_events(cities, debug_limit=None):
    events = []
    for city in cities:
        count = 0
        for slug in get_events(int(city)):
            if debug_limit and count >= debug_limit:
                print(f"[SKILLBOXES] Debug limit of {debug_limit} reached.", file=sys.stderr)
                break
            details = get_event_details(slug)
            if details and details["city_id"] == city:
                details["tickets"] = get_event_tickets(slug)
                events.append(details)
            count += 1

    return events


def events():
    return transform("skillboxes", json.dumps(fetch_events(CITIES, SKILLBOX_DEBUG_LIMIT)))
