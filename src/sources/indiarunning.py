"""
India Running Event Scraper

Fetches running/sports event data from indiarunning.com API and converts to Schema.org SportsEvent format.

API: POST https://registrations-api.indiarunning.com/ir/events/autoCompleteEvents
Request: {"type":"event_city","name":"Bengaluru"}
"""

import json
from bs4 import BeautifulSoup
from datetime import datetime
from common.session import get_cached_session
from common.tz import IST

API_URL = "https://registrations-api.indiarunning.com/ir/events/autoCompleteEvents"
BASE_URL = "https://indiarunning.com"

session = get_cached_session(allowable_methods=["GET", "POST"], allowable_codes=(200, 201))


def fetch_events():
    """Fetch events from the API."""
    response = session.post(
        API_URL,
        json={"type": "event_city", "name": "Bengaluru"},
    )
    if response.status_code not in (200, 201):
        print(f"[INDIARUNNING] Failed to fetch events: {response.status_code}")
        return []
    return response.json().get("events", [])


def html_to_text(html_content):
    """Convert HTML content to plain text."""
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n").strip()


def parse_datetime(dt_str):
    """Parse ISO datetime string to IST datetime."""
    if not dt_str:
        return None
    # Parse UTC datetime (ends with Z or has timezone)
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    # Convert to IST
    return dt.astimezone(IST)


def convert_to_schema_org(event):
    """Convert API event to Schema.org SportsEvent format."""
    event_id = event.get("id")
    slug = event.get("slug", "")
    title = event.get("title", "").strip()

    if not title:
        return None

    # Parse dates
    event_date = event.get("eventDate", {})
    start_dt = parse_datetime(event_date.get("start"))
    end_dt = parse_datetime(event_date.get("end"))

    if not start_dt:
        return None

    # Get description from aboutRace HTML
    about_race = event.get("aboutRace", [])
    description = ""
    if about_race and about_race[0].get("content"):
        description = html_to_text(about_race[0]["content"])

    # Get image
    image_urls = event.get("imageUrls", [])
    image = image_urls[0] if image_urls else ""

    # Get location
    loc_info = event.get("locationInfo", {})
    location = {
        "@type": "Place",
        "name": loc_info.get("area", ""),
        "address": {
            "@type": "PostalAddress",
            "streetAddress": loc_info.get("line1", ""),
            "addressLocality": loc_info.get("city", ""),
            "addressRegion": loc_info.get("state", ""),
            "postalCode": loc_info.get("pinCode", ""),
            "addressCountry": loc_info.get("country", "India"),
        },
    }

    # Add geo coordinates if available
    if loc_info.get("latitude") and loc_info.get("longitude"):
        location["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": loc_info["latitude"],
            "longitude": loc_info["longitude"],
        }

    # Get sport type
    sports_type = event.get("sportsType", [])
    sport = sports_type[0] if sports_type else "Running"

    # Build event URL
    url = f"{BASE_URL}/events/{slug}" if slug else ""

    schema_event = {
        "@type": "SportsEvent",
        "name": title,
        "url": url,
        "startDate": start_dt.isoformat(),
        "endDate": end_dt.isoformat() if end_dt else start_dt.isoformat(),
        "description": description,
        "image": image,
        "location": location,
        "sport": sport,
    }

    # Build offers from price and categories
    price = event.get("price")
    currency = event.get("currency", "INR")
    categories = event.get("categories", [])

    if categories:
        offers = []
        for cat in categories:
            offer = {
                "@type": "Offer",
                "name": cat.get("category", ""),
                "price": str(price) if price else "0",
                "priceCurrency": currency,
            }
            # Add availability based on status
            if cat.get("status") == "available":
                offer["availability"] = "http://schema.org/InStock"
            elif cat.get("status") == "sold_out":
                offer["availability"] = "http://schema.org/SoldOut"
            offers.append(offer)
        schema_event["offers"] = offers
    elif price:
        schema_event["offers"] = [{
            "@type": "Offer",
            "price": str(price),
            "priceCurrency": currency,
        }]

    # Add organizer if available
    if event.get("orgName"):
        schema_event["organizer"] = {
            "@type": "Organization",
            "name": event["orgName"],
        }

    return schema_event


def main():
    events = fetch_events()
    schema_events = []

    for event in events:
        schema_event = convert_to_schema_org(event)
        if schema_event:
            schema_events.append(schema_event)

    # Sort by start date
    schema_events.sort(key=lambda x: x["startDate"])

    with open("out/indiarunning.json", "w") as f:
        json.dump(schema_events, f, indent=2)

    print(f"[INDIARUNNING] {len(schema_events)} events")


if __name__ == "__main__":
    main()
