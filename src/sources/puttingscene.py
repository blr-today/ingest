"""
PuttingScene Event Scraper

Uses the v2 API the Android app talks to (no auth needed):
- GET /api/events?per_page=N&cursor=C lists events, paginated by cursor
- GET /api/events/{id} has description, slots and ticket tiers per slot

Each upcoming slot becomes one schema.org Event.
"""

import json
import logging
from ..common.fetch import Fetch

logger = logging.getLogger("PUTTINGSCENE")

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO, format="[%(name)s] - %(levelname)s - %(message)s"
    )

API_BASE = "https://v2.api.puttingscene.com/api/events"
HEADERS = {"accept": "application/json"}

fetcher = Fetch(
    cache={
        "days": 1,
        "allowable_codes": (200,),
        "allowable_methods": ["GET"],
    },
)


def fetch_event_list() -> list:
    events, params = [], {"per_page": 50}
    while True:
        res = fetcher.get(url=API_BASE, params=params, headers=HEADERS)
        if res.status_code != 200:
            logger.error(f"Failed to fetch events: {res.status_code}")
            break
        data = res.json()
        events.extend(data.get("data", []))
        page = data.get("page") or {}
        if not page.get("has_more") or not page.get("next_cursor"):
            break
        params["cursor"] = page["next_cursor"]
    logger.info(f"Fetched {len(events)} events")
    return events


def fetch_event_details(event_id: str) -> dict | None:
    res = fetcher.get(url=f"{API_BASE}/{event_id}", headers=HEADERS)
    if res.status_code != 200:
        logger.warning(f"Failed to fetch details for event {event_id}: {res.status_code}")
        return None
    return res.json()


def make_offers(slot: dict) -> list:
    offers = []
    for tier in slot.get("ticket_tiers", []):
        price = tier.get("price_with_tax") or tier.get("price") or {}
        available = tier.get("available_capacity") or 0
        offer = {
            "@type": "Offer",
            "name": tier.get("name", ""),
            "price": f"{price.get('amount_in_minor_units', 0) / 100:.2f}",
            "priceCurrency": price.get("currency", "INR"),
            "availability": "https://schema.org/SoldOut"
            if tier.get("is_sold_out") or available <= 0
            else "https://schema.org/InStock",
        }
        if available > 0:
            offer["remainingAttendeeCapacity"] = available
        offers.append(offer)
    return offers


def make_events(event: dict) -> list:
    title = (event.get("title") or "").strip()
    if not title or "test" in title.lower():
        return []

    images = event.get("images") or []
    primary = next((i for i in images if i.get("is_primary")), images[0] if images else {})
    venue = event.get("venue") or {}
    base = {
        "@type": "Event",
        "name": title,
        "url": f"https://puttingscene.com/events/{event['id']}",
        "description": event.get("short_description") or event.get("description") or "",
        "image": primary.get("url") or primary.get("external_url") or "",
        "location": {
            "name": venue.get("name", ""),
            "address": f"{venue.get('name', '')}, Bangalore",
        },
    }
    if venue.get("google_maps_url"):
        base["location"]["url"] = venue["google_maps_url"]
    if event.get("external_url"):
        base["sameAs"] = event["external_url"]
    if (event.get("org_details") or {}).get("name"):
        base["organizer"] = {"@type": "Organization", "name": event["org_details"]["name"]}

    events = []
    for slot in event.get("slots", []):
        if slot.get("is_in_past") or not slot.get("start_at"):
            continue
        e = dict(base, startDate=slot["start_at"], endDate=slot.get("end_at") or slot["start_at"])
        offers = make_offers(slot)
        if event.get("is_paid") and offers:
            e["offers"] = offers
        elif not event.get("is_paid"):
            e["isAccessibleForFree"] = True
        events.append(e)
    return events


def fetch_putting_scenes() -> list:
    all_events = []
    for event in fetch_event_list():
        if event.get("is_in_past"):
            continue
        details = fetch_event_details(event["id"])
        if details:
            all_events.extend(make_events(details))
    return sorted(all_events, key=lambda x: (x["startDate"], x["url"]))


if __name__ == "__main__":
    with open("out/puttingscene.json", "w") as f:
        events = fetch_putting_scenes()
        json.dump(events, f, indent=2)
        print(f"[PUTTINGSCENE] {len(events)} events")
