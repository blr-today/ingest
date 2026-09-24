import html
import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

from common.session import get_cached_session
from common.tz import IST

SITE_URL = "https://bangaloreastronomyclub.com"
EVENTS_API = f"{SITE_URL}/wp-json/tribe/events/v1/events"

CATEGORY_TYPE = {"Astro-Photography Exhibition": "ExhibitionEvent"}
DEFAULT_TYPE = "EducationEvent"

# Districts/hill-stations BAC runs stargazing camps at, outside city limits
OUTSIDE_BLR_KEYWORDS = (
    "kanakapura", "kanakpura", "ramanagara", "ramnagar", "chikkaballapur",
    "chikballapur", "nandi post", "nandi hills", "kolar", "coorg", "kodagu",
    "mysore", "mysuru", "chikmagalur", "chikkamagaluru", "skandagiri",
)


def strip_html(raw):
    return BeautifulSoup(html.unescape(raw or ""), "html.parser").get_text().strip()


def parse_ist(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)


def guess_event_type(categories):
    for c in categories or []:
        if c.get("name") in CATEGORY_TYPE:
            return CATEGORY_TYPE[c["name"]]
    return DEFAULT_TYPE


def is_outside_blr(venue):
    text = " ".join(
        str(venue.get(k) or "") for k in ("venue", "address", "city", "stateprovince")
    ).lower()
    return any(kw in text for kw in OUTSIDE_BLR_KEYWORDS)


def make_location(venue):
    address = {"@type": "PostalAddress", "addressCountry": "India"}
    if venue.get("address"):
        address["streetAddress"] = venue["address"]
    if venue.get("city"):
        address["addressLocality"] = venue["city"]
    if venue.get("stateprovince"):
        address["addressRegion"] = venue["stateprovince"]
    if venue.get("zip"):
        address["postalCode"] = venue["zip"]
    return {
        "@type": "Place",
        "name": venue.get("venue") or "Bangalore Astronomy Club",
        "address": address,
    }


def fetch_min_price(session, url):
    # Ticket prices aren't in the REST API, only in per-package data attrs on the page
    try:
        page = session.get(url, timeout=30).text
    except Exception:
        return None
    prices = [int(p) for p in re.findall(r'data-adult-price="(\d+)"', page)]
    return min(prices) if prices else None


def fetch_events(session):
    events, page = [], 1
    while True:
        data = session.get(EVENTS_API, params={"per_page": 50, "page": page}, timeout=30).json()
        events.extend(data.get("events", []))
        if page >= data.get("total_pages", 1):
            return events
        page += 1


def make_event(session, e, now):
    start_dt = parse_ist(e["start_date"])
    if start_dt < now:
        return None
    end_dt = parse_ist(e["end_date"])
    venue = e.get("venue") or {}
    url = e["url"]

    event = {
        "@context": "https://schema.org",
        "@type": guess_event_type(e.get("categories")),
        "name": strip_html(e["title"]),
        "description": strip_html(e["description"]),
        "startDate": start_dt.isoformat(),
        "endDate": end_dt.isoformat(),
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
        "url": url,
        "location": make_location(venue),
        "organizer": {"@type": "Organization", "name": "Bangalore Astronomy Club", "url": SITE_URL},
    }

    image = (e.get("image") or {}).get("url")
    if image:
        event["image"] = image

    min_price = fetch_min_price(session, url)
    if min_price == 0:
        event["isAccessibleForFree"] = True
    elif min_price is not None:
        event["offers"] = [
            {
                "@type": "Offer",
                "price": str(min_price),
                "priceCurrency": "INR",
                "url": url,
                "availability": "https://schema.org/InStock",
            }
        ]

    if is_outside_blr(venue):
        event["keywords"] = ["NOTINBLR"]

    return event


def main():
    session = get_cached_session()
    now = datetime.now(IST)
    raw_events = fetch_events(session)
    events = [ev for ev in (make_event(session, e, now) for e in raw_events) if ev]

    with open("out/bac.json", "w") as f:
        json.dump(events, f, indent=2)

    print(f"[BAC] {len(events)} events")


if __name__ == "__main__":
    main()
