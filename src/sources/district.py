import json
import sys
import curl_cffi
import requests
from common import USER_AGENT_HEADERS
from common.jsonld import JsonLdExtractor
from common.remote import find_event
from common.session import get_cached_session

URL = "https://www.district.in/gw/web/get_discovery_results"
LAT, LNG = 12.9716, 77.5946
CITIES = ("Bengaluru", "Bangalore")
HEADERS = {
    "content-type": "application/json",
    "x-guest-token": "1212",
    "x-app-type": "ed_web",
    "x-available-tabs": "events",
    "x-user-lat": str(LAT),
    "x-user-lng": str(LNG),
}
LOCATION = {"user_lat": LAT, "user_lng": LNG, "gps_lat": LAT, "gps_lng": LNG}
DEBUG_HEADERS = ("content-type", "server", "server-timing", "x-cache", "akamai-grn")


def log(*args):
    print("[DISTRICT]", *args, file=sys.stderr)


def describe(client, r):
    headers = {k: r.headers.get(k) for k in DEBUG_HEADERS if r.headers.get(k)}
    log(client, r.status_code, len(r.content), "bytes", headers)


def post(session, body):
    r = session.post(URL, headers=HEADERS, json=body, timeout=30)
    describe("requests", r)
    try:
        return r.json()
    except ValueError:
        log("non-JSON body:", r.text[:500])
    r = curl_cffi.post(
        URL, headers=HEADERS, json=body, timeout=30, impersonate="chrome"
    )
    describe("curl_cffi", r)
    try:
        return r.json()
    except ValueError:
        log("non-JSON body:", r.text[:500])
        raise


def pages(session, limit=300):
    body = {"location": LOCATION, "layout_type": "events_home_v2"}
    for page in range(limit):
        response = post(session, body)["EDSResponse"]
        log("page", page, "has_more", response.get("has_more"))
        yield response
        if not response.get("has_more"):
            break
        body = {
            "location": LOCATION,
            "layout_type": "events_home_v2",
            "request_type": "load_more",
            "postback_params": response["postback_params"],
        }


def events(node):
    if isinstance(node, dict):
        if "EventData" in node:
            yield node["EventData"]
        for value in node.values():
            yield from events(value)
    elif isinstance(node, list):
        for value in node:
            yield from events(value)


def page_event(session, url):
    try:
        r = session.get(url, headers=USER_AGENT_HEADERS, timeout=30)
        data = JsonLdExtractor().extract(r.text)
    except Exception as e:
        log("failed", url, e)
        return None
    event = None
    for x in data:
        if x.get("@graph"):
            event = event or find_event(x["@graph"])
    return event or find_event(data)


if __name__ == "__main__":
    slugs = set()
    for response in pages(requests.Session()):
        for event in events(response.get("rails")):
            if event.get("city") in CITIES and event.get("event_slug"):
                slugs.add(event["event_slug"])
    log(len(slugs), "Bengaluru events")
    session = get_cached_session()
    found = []
    for slug in sorted(slugs):
        url = f"https://district.in/{slug}/event"
        event = page_event(session, url)
        if event:
            event.setdefault("url", url)
            found.append(event)
    log(len(found), "pages had event data")
    json.dump(found, sys.stdout, indent=2)
