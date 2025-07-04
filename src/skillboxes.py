from urllib.parse import urlparse, parse_qs
from common.fetch import Fetch
import requests
import json
import sys

BASE_URL = "https://www.skillboxes.com/servers"


def get_events(city, page=1):
    payload = {
        "page": page,
        "city": city,
    }

    headers = {"Content-Type": "application/json"}

    res = requests.post(
        "https://www.skillboxes.com/servers/v1/api/event-new/get-event",
        json=payload,
        headers=headers,
    ).json()
    for item in res["items"]:
        yield item['slug']
    if res["next"]:
        yield from get_events(city, page + 1)


# curl 'https://www.skillboxes.com/servers/v3/api/event-new/event-details' - H 'Content-Type: application/json' - -data-raw '{"slug":"The-Kitty-Ko-Royale-Ft-Usha-Uthup-Rani-Kohenur-Bangalore-Edition"}'

# curl 'https://www.skillboxes.com/servers/v3/api/event-new/event-tickets' - H 'Content-Type: application/json' - -data-raw '{"slug":"The-Kitty-Ko-Royale-Ft-Usha-Uthup-Rani-Kohenur-Bangalore-Edition"}'

# curl 'https://www.skillboxes.com/servers/v3/api/get-meta-details' - H 'Content-Type: application/json' - -data-raw '{"slug":"The-Kitty-Ko-Royale-Ft-Usha-Uthup-Rani-Kohenur-Bangalore-Edition","opcode":"events"}'

def get_event_details(session, slug):
    headers = {"Content-Type": "application/json"}
    payload = {"slug": slug}
    details = session.post(
        "https://www.skillboxes.com/servers/v3/api/event-new/event-details",
        json=payload,
        headers=headers,
    ).json()['data']

    try:
        r = session.post(
            "https://www.skillboxes.com/servers/v3/api/event-new/event-tickets",
            json=payload,
            headers=headers,
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


def __main__(city):
    session = Fetch(cache={"serializer": "json"})
    events = []
    for slug in get_events(city):
        details = get_event_details(session, slug)
        if details:
            events.append(details)

    with open("out/skillboxes.jsonnet", "w") as f:
        json.dump(events, f, indent=2)


if __name__ == "__main__":
    if sys.argv[1]:
        __main__(sys.argv[1])
    else:
        raise Exception("City ID is required. Bangalore=9")
