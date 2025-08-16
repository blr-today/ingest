from urllib.parse import urlparse, parse_qs
from common.fetch import Fetch
import requests
import json
import sys

BASE_URL = "https://www.skillboxes.com/servers"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; blr.today-bot; +https://blr.today/bot/)",
    "Accept": "application/json",
}


def get_events(city, page=1):
    payload = {
        "default_city": city,
        "opcode": "search",
        "page": page,
        "type": "fetchAll",
    }

    res = requests.post(
        "https://www.skillboxes.com/servers/v3/api/event-new/get-event",
        json=payload,
        headers=HEADERS,
    )
    if res.status_code != 200:
        print("[SKILLBOXES] Failed to get list of events.", file=sys.stderr)
        sys.exit(0)
    data = res.json()
    for item in data["items"]:
        yield item["slug"]
    if data["next"]:
        yield from get_events(city, page + 1)


def get_event_details(session, slug):
    payload = {"slug": slug}
    res = session.post(
        "https://www.skillboxes.com/servers/v3/api/event-new/event-details",
        json=payload,
        headers=HEADERS,
    )

    if res.status_code != 200:
        print(f"[SKILLBOXES] Failed to get details for event {slug}.", file=sys.stderr)
        return None

    return res.json()["data"]


def get_event_tickets(session, slug):
    try:
        payload = {"slug": slug}
        res = session.post(
            "https://www.skillboxes.com/servers/v3/api/event-new/event-tickets",
            json=payload,
            headers=HEADERS,
        ).json()

        if res["success"] == False:
            return []

        return res["data"]
    except Exception as e:
        if "more than 100 headers" in str(e):
            return []
        else:
            print(
                f"[SKILLBOXES] Error fetching tickets for event {slug}: {e}",
                file=sys.stderr,
            )
            return []


def __main__(cities):
    session = Fetch(cache={"serializer": "json"})
    events = []
    for city in cities:
        for slug in get_events(city):
            details = get_event_details(session, slug)
            if details and details["city_id"] == city:
                details["tickets"] = get_event_tickets(session, slug)
                events.append(details)

    with open("out/skillboxes.jsonnet", "w") as f:
        json.dump(events, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cities = sys.argv[1:]
        __main__(cities)
    else:
        raise Exception("City ID is required. Bangalore=9")
