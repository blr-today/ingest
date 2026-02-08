"""
PuttingScene Event Scraper

Fetches event data from the PuttingScene API and converts it to Schema.org Event format.

API: https://api.puttingscene.com/api/v1/events/events/

Process:
1. Fetch paginated event list with filters:
   - publish_date__lte: today (already published)
   - event_date__gte: today (future events)
   - approval_status: approved
   - is_private: false
   - custom_filter: true

2. For each event, fetch details from /events/events/{id}/ to get:
   - source_url: original event URL (used as sameAs)
   - slots: for PARTNER events that use slot-based scheduling

3. Convert to Schema.org Event format:
   - Regular events: have event_date set, create one Event per event
   - Slot-based events: have slots[] instead of event_date, create one Event per slot
     (e.g., a workshop with morning and afternoon sessions becomes two Events)

4. Pricing from ticket_tiers:
   - Each tier has slot-specific availability via available_capacity[{slot_id, available}]
   - Note: PARTNER events may have is_paid=False but priced ticket_tiers, so we check both
"""

import json
import logging
from datetime import datetime, timedelta
from ..common.fetch import Fetch
from ..common.tz import IST

logger = logging.getLogger("PUTTINGSCENE")

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO, format="[%(name)s] - %(levelname)s - %(message)s"
    )

API_BASE = "https://api.puttingscene.com/api/v1/events/events/"
DEFAULT_EVENT_DURATION_HOURS = 2

fetcher = Fetch(
    cache={
        "days": 1,
        "allowable_codes": (200,),
        "allowable_methods": ["GET"],
    },
)


def fetch_event_details(event_id: int) -> dict | None:
    """Fetch detailed event info including source_url and slots."""
    res = fetcher.get(url=f"{API_BASE}{event_id}/")
    if res.status_code != 200:
        logger.warning(f"Failed to fetch details for event {event_id}: {res.status_code}")
        return None
    return res.json()


def fetch_events_page(params: dict) -> dict:
    """Fetch a single page of events from the API."""
    res = fetcher.get(url=API_BASE, params=params)
    if res.status_code != 200:
        logger.error(f"Failed to fetch events: {res.status_code}")
        return {"results": [], "next": None}
    return res.json()


def fetch_all_events_for_source(event_source_type: str | None) -> list:
    """Fetch all pages of events for a given source type."""
    today = datetime.now().strftime("%Y-%m-%d")

    params = {
        "publish_date__lte": today,
        "event_date__gte": today,
        "custom_filter": "true",
        "approval_status": "approved",
        "is_private": "false",
        "page": 1,
    }

    if event_source_type:
        params["event_source_type"] = event_source_type

    all_events = []
    while True:
        logger.debug(f"Fetching page {params['page']} for source={event_source_type}")
        data = fetch_events_page(params)
        all_events.extend(data.get("results", []))

        if not data.get("next"):
            break
        params["page"] += 1

    logger.info(f"Fetched {len(all_events)} events for source={event_source_type}")
    return all_events


def build_offers_for_slot(ticket_tiers: list, slot_id: int) -> list:
    """Build offers from ticket_tiers for a specific slot."""
    offers = []
    for tier in ticket_tiers:
        if not tier.get("is_active", True):
            continue

        offer = {
            "@type": "Offer",
            "name": tier.get("name", ""),
            "price": tier.get("price", "0"),
            "priceCurrency": "INR",
        }

        # Find availability for this specific slot
        available_capacity = tier.get("available_capacity", [])
        for cap in available_capacity:
            if cap.get("slot_id") == slot_id:
                available = cap.get("available", 0)
                if available > 0:
                    offer["availability"] = "http://schema.org/InStock"
                    offer["remainingAttendeeCapacity"] = available
                break

        offers.append(offer)

    return offers


def convert_slot_to_schema_org(event: dict, slot: dict, source_url: str | None = None) -> dict | None:
    """Convert a slot-based event to Schema.org Event format."""
    try:
        event_id = event.get("id")
        slot_id = slot.get("id")
        title = event.get("title", "").strip()

        if not title or "test" in title.lower():
            return None

        # Parse slot dates
        slot_date = slot.get("date")
        start_time = slot.get("start_time", "00:00:00")
        end_time = slot.get("end_time")

        if not slot_date or not slot.get("is_active", True):
            return None

        # Filter out past slots
        today = datetime.now().date()
        slot_date_obj = datetime.strptime(slot_date, "%Y-%m-%d").date()
        if slot_date_obj < today:
            return None

        # Build start datetime
        start_dt = datetime.strptime(f"{slot_date} {start_time}", "%Y-%m-%d %H:%M:%S")
        start_dt = start_dt.replace(tzinfo=IST)

        # Build end datetime
        if end_time:
            end_date = slot.get("end_date", slot_date)
            end_dt = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M:%S")
            end_dt = end_dt.replace(tzinfo=IST)
        else:
            end_dt = start_dt + timedelta(hours=DEFAULT_EVENT_DURATION_HOURS)

        # Get description
        description = event.get("short_description") or event.get("description") or ""

        # Get image
        images = event.get("images", [])
        image = images[0].get("image_url", "") if images else ""

        # Get venue/location
        venue = event.get("venue") or {}
        location_name = venue.get("name", "")
        location_address = venue.get("full_address") or f"{location_name}, {venue.get('city', 'Bangalore')}"
        location_url = venue.get("google_url", "")

        schema_event = {
            "@type": "Event",
            "name": title,
            "url": f"https://puttingscene.com/events/{event_id}",
            "startDate": start_dt.isoformat(),
            "endDate": end_dt.isoformat(),
            "description": description,
            "image": image,
            "location": {
                "name": location_name,
                "address": location_address,
            },
        }

        if location_url:
            schema_event["location"]["url"] = location_url

        # Use source_url as sameAs
        if source_url:
            schema_event["sameAs"] = source_url

        # Build offers from ticket_tiers for this slot
        ticket_tiers = event.get("ticket_tiers", [])
        is_paid = event.get("is_paid", False)

        # Check if any ticket tier has a price > 0 (fallback for is_paid=False with priced tiers)
        has_priced_tiers = any(
            float(tier.get("price", 0)) > 0
            for tier in ticket_tiers
            if tier.get("is_active", True)
        )

        if ticket_tiers and (is_paid or has_priced_tiers):
            offers = build_offers_for_slot(ticket_tiers, slot_id)
            if offers:
                schema_event["offers"] = offers
        elif not is_paid and not has_priced_tiers:
            schema_event["isAccessibleForFree"] = True

        return schema_event
    except Exception as e:
        logger.warning(f"Error converting slot {slot.get('id')} for event {event.get('id')}: {e}")
        return None


def convert_to_schema_org(event: dict, source_url: str | None = None) -> dict | None:
    """Convert API event to Schema.org Event format (for events with event_date)."""
    try:
        event_id = event.get("id")
        title = event.get("title", "").strip()

        if not title or "test" in title.lower():
            return None

        # Parse dates
        event_date = event.get("event_date")
        start_time = event.get("start_time", "00:00:00")
        end_time = event.get("end_time")

        if not event_date:
            return None

        # Build start datetime
        start_dt = datetime.strptime(f"{event_date} {start_time}", "%Y-%m-%d %H:%M:%S")
        start_dt = start_dt.replace(tzinfo=IST)

        # Build end datetime
        if end_time:
            end_dt = datetime.strptime(f"{event_date} {end_time}", "%Y-%m-%d %H:%M:%S")
            end_dt = end_dt.replace(tzinfo=IST)
        else:
            end_dt = start_dt + timedelta(hours=DEFAULT_EVENT_DURATION_HOURS)

        # Get description
        description = event.get("short_description") or event.get("description") or ""

        # Get image
        images = event.get("images", [])
        image = images[0].get("image_url", "") if images else ""

        # Get venue/location
        venue = event.get("venue") or {}
        location_name = venue.get("name", "")
        location_address = venue.get("full_address") or f"{location_name}, {venue.get('city', 'Bangalore')}"
        location_url = venue.get("google_url", "")

        schema_event = {
            "@type": "Event",
            "name": title,
            "url": f"https://puttingscene.com/events/{event_id}",
            "startDate": start_dt.isoformat(),
            "endDate": end_dt.isoformat(),
            "description": description,
            "image": image,
            "location": {
                "name": location_name,
                "address": location_address,
            },
        }

        if location_url:
            schema_event["location"]["url"] = location_url

        # Use source_url as sameAs
        if source_url:
            schema_event["sameAs"] = source_url
        elif event.get("is_online") and event.get("online_url"):
            schema_event["sameAs"] = event.get("online_url")

        # Handle pricing
        is_paid = event.get("is_paid", False)
        price = event.get("price", "0")
        ticket_tiers = event.get("ticket_tiers", [])

        # Check if any ticket tier has a price > 0 (fallback for is_paid=False with priced tiers)
        has_priced_tiers = any(
            float(tier.get("price", 0)) > 0
            for tier in ticket_tiers
            if tier.get("is_active", True)
        )

        if ticket_tiers and (is_paid or has_priced_tiers):
            offers = []
            for tier in ticket_tiers:
                if not tier.get("is_active", True):
                    continue
                offer = {
                    "@type": "Offer",
                    "name": tier.get("name", ""),
                    "price": tier.get("price", "0"),
                    "priceCurrency": "INR",
                }
                # Add availability from available_capacity
                available_capacity = tier.get("available_capacity", [])
                total_available = sum(slot.get("available", 0) for slot in available_capacity)
                if total_available > 0:
                    offer["availability"] = "http://schema.org/InStock"
                    offer["remainingAttendeeCapacity"] = total_available
                offers.append(offer)
            if offers:
                schema_event["offers"] = offers
        elif is_paid and price and price != "0" and price != "0.00":
            schema_event["offers"] = [{
                "@type": "Offer",
                "price": price,
                "priceCurrency": "INR",
            }]
        elif not is_paid and not has_priced_tiers:
            schema_event["isAccessibleForFree"] = True

        return schema_event
    except Exception as e:
        logger.warning(f"Error converting event {event.get('id')}: {e}")
        return None


def fetch_putting_scenes() -> list:
    """Fetch all events."""
    all_events = []

    # Fetch all events (no source_type filter returns SCRAPED + PARTNER + INTERNAL)
    events = fetch_all_events_for_source(None)

    for event in events:
        event_id = event.get("id")

        # Fetch detailed event info to get source_url and slots
        details = fetch_event_details(event_id)
        if not details:
            continue

        source_url = details.get("source_url")
        slots = details.get("slots", [])
        event_date = details.get("event_date")

        if event_date:
            # Regular event with event_date
            schema_event = convert_to_schema_org(details, source_url=source_url)
            if schema_event:
                all_events.append(schema_event)
        elif slots:
            # Slot-based event: create one event per slot
            for slot in slots:
                schema_event = convert_slot_to_schema_org(details, slot, source_url=source_url)
                if schema_event:
                    all_events.append(schema_event)

    # Sort by startDate for consistent output
    return sorted(all_events, key=lambda x: (x["startDate"], x["url"]))


if __name__ == "__main__":
    with open("out/puttingscene.json", "w") as f:
        events = fetch_putting_scenes()
        json.dump(events, f, indent=2)
        print(f"[PUTTINGSCENE] {len(events)} events")
