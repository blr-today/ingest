import json
import re
import sys

import ics

from common import USER_AGENT_HEADERS
from common.jsonld import JsonLdExtractor
from common.session import get_cached_session

# Usage: python -m src.sources.meetup <group-slug>, writes out/<group-slug>.json
NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
PRICE = re.compile(r"₹\s?(\d+) per person")


def event_urls(session, group):
    r = session.get(f"https://www.meetup.com/{group}/events/ical/", headers=USER_AGENT_HEADERS)
    r.raise_for_status()
    return [str(e.url) for e in sorted(ics.Calendar(r.text).events, key=lambda e: e.begin) if e.url]


def venues(node):
    if isinstance(node, dict):
        if node.get("__typename") == "Venue" and node.get("lat") and node.get("lng"):
            yield node
        for value in node.values():
            yield from venues(value)
    elif isinstance(node, list):
        for value in node:
            yield from venues(value)


def page_event(state, url):
    events = [v for k, v in state.items() if k.startswith("Event:")]
    return next((e for e in events if e.get("eventUrl") == url), events[0] if events else {})


def enrich(event, props, url):
    details = page_event(props.get("__APOLLO_STATE__", {}), url)
    if details.get("description"):
        event["description"] = details["description"]
    seats, going = details.get("maxTickets"), details.get('rsvps({"filter":{"rsvpStatus":["YES"]}})')
    if seats:
        event["maximumAttendeeCapacity"] = seats
        if going:
            event["remainingAttendeeCapacity"] = max(seats - going["totalCount"], 0)
    price = PRICE.search(event.get("description", ""))
    if price:
        event["offers"] = {"@type": "Offer", "price": price.group(1), "priceCurrency": "INR"}
    location = event.get("location")
    venue = next(venues(props), None)
    if isinstance(location, dict) and venue and venue.get("name") == location.get("name"):
        location["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": venue["lat"],
            "longitude": venue["lng"],
        }


def make_event(session, url):
    html = session.get(url, headers=USER_AGENT_HEADERS).text
    event = next((x for x in JsonLdExtractor().extract(html) if x.get("@type") == "Event"), None)
    if not event:
        print(f"[MEETUP] No event found at {url}", file=sys.stderr)
        return None
    event["url"] = url
    match = NEXT_DATA.search(html)
    if match:
        enrich(event, json.loads(match.group(1))["props"]["pageProps"], url)
    return event


if __name__ == "__main__":
    group = sys.argv[1]
    session = get_cached_session()
    events = [e for e in (make_event(session, url) for url in event_urls(session, group)) if e]
    with open(f"out/{group}.json", "w") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f"[MEETUP/{group}] {len(events)} events")
