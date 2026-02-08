"""
Penciljam Event Scraper

Fetches sketching event data from penciljam.com and converts to Schema.org Event format.

Process:
1. Fetch https://penciljam.com/main/events-2/ to get event listing
2. Extract event URLs from .em-event divs
3. Fetch iCal version of each event (append /ical/ to URL)
4. Parse iCal and convert to Schema.org Event format
"""

import json
from datetime import timedelta
from bs4 import BeautifulSoup
import ics
from common.session import get_cached_session
from common.tz import IST

EVENTS_URL = "https://penciljam.com/main/events-2/"

session = get_cached_session()


def fetch_event_urls():
    """Fetch the events page and extract event URLs."""
    response = session.get(EVENTS_URL)
    if response.status_code != 200:
        print(f"[PENCILJAM] Failed to fetch events page: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    urls = []

    for event_div in soup.select(".em-event"):
        # Get URL from data-href attribute or from the title link
        url = event_div.get("data-href")
        if not url:
            link = event_div.select_one(".em-item-title a")
            if link:
                url = link.get("href")
        if url:
            urls.append(url)

    return urls


def fetch_ical(event_url):
    """Fetch iCal version of an event."""
    ical_url = event_url.rstrip("/") + "/ical/"
    response = session.get(ical_url)
    if response.status_code != 200:
        print(f"[PENCILJAM] Failed to fetch iCal for {event_url}: {response.status_code}")
        return None
    return response.text


def parse_ical_event(ical_text, event_url):
    """Parse iCal text and convert to Schema.org Event format."""
    try:
        calendar = ics.Calendar(ical_text)

        for event in calendar.events:
            if not event.name:
                continue

            # Handle same start/end time
            if event.end == event.begin:
                event.end = event.begin + timedelta(hours=2)

            # Extract location name from summary if it contains " at "
            location_name = event.location or ""
            if " at " in event.name:
                parts = event.name.split(" at ", 1)
                if len(parts) == 2:
                    location_name = parts[1].strip()

            schema_event = {
                "name": event.name,
                "url": event_url,
                "startDate": event.begin.astimezone(IST).isoformat(),
                "endDate": event.end.astimezone(IST).isoformat(),
                "description": event.description or "",
            }

            # Add location
            if location_name:
                schema_event["location"] = {
                    "@type": "Place",
                    "name": location_name,
                }
                # If original location is a URL (maps link), add it
                if event.location and event.location.startswith("http"):
                    schema_event["location"]["url"] = event.location

            return schema_event

        return None
    except Exception as e:
        print(f"[PENCILJAM] Error parsing iCal for {event_url}: {e}")
        return None


def main():
    event_urls = fetch_event_urls()
    events = []

    for url in event_urls:
        ical_text = fetch_ical(url)
        if ical_text:
            event = parse_ical_event(ical_text, url)
            if event:
                events.append(event)

    # Sort by start date
    events.sort(key=lambda x: x["startDate"])

    with open("out/penciljam.json", "w") as f:
        json.dump(events, f, indent=2)

    print(f"[PENCILJAM] {len(events)} events")


if __name__ == "__main__":
    main()
