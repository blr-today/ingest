import json
import datetime
import requests
from common.tz import IST

BASE_URL = "https://bangalorechessclub.in"
API_URL = BASE_URL + "/api/events"


def fetch_events(session):
    page = 1
    while True:
        data = session.get(API_URL, params={"page": page}, timeout=30).json()
        yield from data["events"]
        if page * data["page_size"] >= data["total"] or not data["events"]:
            break
        page += 1


def to_ist(ts):
    return (
        datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        .astimezone(IST)
        .isoformat()
    )


def make_event(e):
    url = f"{BASE_URL}/events/{e['slug']}"
    venue = e.get("venue") or {}
    price = e.get("price_inr") or 0
    event = {
        "@context": "https://schema.org",
        "@type": "SocialEvent",
        "name": f"{e['title']} - Bangalore Chess Club",
        "description": e.get("description"),
        "startDate": to_ist(e["starts_at"]),
        "endDate": to_ist(e["ends_at"]),
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
        "location": {
            "@type": "Place",
            "name": venue.get("name"),
            "address": ", ".join(
                x for x in [venue.get("address"), "Bengaluru", "India"] if x
            ),
        },
        "isAccessibleForFree": price == 0,
        "offers": [
            {
                "@type": "Offer",
                "price": str(price),
                "priceCurrency": "INR",
                "availability": (
                    "https://schema.org/InStock"
                    if e.get("is_available")
                    else "https://schema.org/SoldOut"
                ),
                "url": url,
            }
        ],
        "organizer": {
            "@type": "Organization",
            "name": "Bangalore Chess Club",
            "url": BASE_URL,
        },
        "keywords": ["bangalore chess club", "chess"],
        "url": url,
    }
    if venue.get("maps_link"):
        event["location"]["hasMap"] = venue["maps_link"]
    if e.get("image_path"):
        event["image"] = (
            e["image_path"]
            if e["image_path"].startswith("http")
            else BASE_URL + "/" + e["image_path"].lstrip("/")
        )
    return event


if __name__ == "__main__":
    session = requests.Session()
    events = [make_event(e) for e in fetch_events(session) if not e.get("is_past")]
    with open("out/bcc.json", "w") as f:
        json.dump(events, f, indent=2)
