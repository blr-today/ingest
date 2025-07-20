from urllib.parse import urlparse, parse_qs
from common.fetch import Fetch
import requests
import json
import sys

BASE_URL = "https://www.skillboxes.com/servers"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; blr.today-bot; +httpss://blr.today/bot/)"
}

def get_events(city, page=1):
    payload = {
        "city": city,
        "page": page,
        "type": "fetchAll"
    }

    res = requests.post(
        "https://www.skillboxes.com/servers/v3/api/event-new/get-event",
        json=payload,
        headers=HEADERS,
    ).json()
    for item in res["items"]:
        yield item['slug']
    if res["next"]:
        yield from get_events(city, page + 1)

def get_event_details(session, slug):
    payload = {"slug": slug}
    details = session.post(
        "https://www.skillboxes.com/servers/v3/api/event-new/event-details",
        json=payload,
        headers=HEADERS,
    ).json()['data']

    try:
        r = session.post(
            "https://www.skillboxes.com/servers/v3/api/event-new/event-tickets",
            json=payload,
            headers=HEADERS,
        ).json()

        if r['success'] == False:
            return None
        details['tickets'] = r['data']
        return details
    except Exception as e:
        if "more than 100 headers" in str(e):
            return None
        else:
            raise e


def __main__(cities):
    session = Fetch(cache={"serializer": "json"})
    events = []
    for city in cities:
        for slug in get_events(city):
            details = get_event_details(session, slug)
            if details:
                events.append(details)

    with open("out/skillboxes.jsonnet", "w") as f:
        json.dump(events, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cities = sys.argv[1:]
        __main__(cities)
    else:
        raise Exception("City ID is required. Bangalore=9")
