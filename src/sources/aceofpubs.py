import datetime
import html
import json
import re

from ..common import USER_AGENT_HEADERS
from ..common.remote import page_event
from ..common.session import get_cached_session

SITEMAP = "https://aceofpubs.com/wp-sitemap-posts-mep_events-1.xml"
ORGANIZER = {
    "@type": "Organization",
    "name": "Ace of Pubs",
    "url": "https://aceofpubs.com/",
}


def event_urls(session):
    xml = session.get(SITEMAP, headers=USER_AGENT_HEADERS, timeout=30).text
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def clean(event, url):
    name = html.unescape(event["name"])
    event["name"] = re.sub(r"\s*[–-]\s*(Bengaluru|Bangalore)\s*$", "", name)
    event["description"] = html.unescape(event.get("description") or "")
    event["url"] = url
    # The events plugin fills these with placeholders
    event["organizer"] = ORGANIZER
    event.pop("performer", None)
    event.pop("previousStartDate", None)
    event["eventStatus"] = "https://schema.org/EventScheduled"
    address = event.get("location", {}).get("address")
    if isinstance(address, dict):
        address["addressRegion"] = "Karnataka"
    return event


def in_bangalore(event):
    location = json.dumps(event.get("location", {})).lower()
    return "bengaluru" in location or "bangalore" in location


def upcoming(event):
    end = event.get("endDate") or event.get("startDate")
    try:
        return datetime.datetime.fromisoformat(end) > datetime.datetime.now(
            datetime.timezone.utc
        )
    except TypeError, ValueError:
        return False


def events():
    session = get_cached_session()
    events = []
    for url in event_urls(session):
        event = page_event(session, url)
        if event and in_bangalore(event) and upcoming(event):
            events.append(clean(event, url))
    return events
