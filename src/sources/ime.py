import re
from datetime import datetime

from bs4 import BeautifulSoup

from ..common import USER_AGENT_HEADERS, icalendar
from ..common.jsonld import JsonLdExtractor
from ..common.session import get_cached_session
from ..common.tz import IST

BASE = "https://indianmusicexperience.org/"
LISTING = BASE + "events/"
# The page shows "5:00 pm - 7:00 pm", or just "5:00 pm" when no end is set
START_ONLY = re.compile(r"\d{1,2}:\d{2} ?[ap]m", re.I)
# Divi page-builder shortcodes leak into the iCal description
SHORTCODE = re.compile(r"\[/?et_pb_[^\]]*\]")
MUSEUM = {
    "@type": "Place",
    "name": "IME Museum",
    "address": "IME Museum, JP Nagar 7th phase, Bengaluru – 560078",
}


def get(session, url):
    response = session.get(url, headers=USER_AGENT_HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def upcoming(page):
    listed = [i for i in JsonLdExtractor().extract(page) if i.get("@type") == "Event"]
    # Past events stay listed, so an empty listing means the page changed
    if not listed:
        raise ValueError(f"No events in {LISTING}")
    today = datetime.now(IST).date().isoformat()
    # Skip past events before fetching their pages
    return [(i["url"], i) for i in listed if i["endDate"] >= today]


def place(listed):
    # Museum events sometimes leave the place blank
    name = (listed.get("name") or "").strip()
    if not name:
        return MUSEUM
    return {"@type": "Place", "name": name, "address": listed.get("address") or ""}


def make_event(session, url, listed):
    page = BeautifulSoup(get(session, url), "html.parser")
    link = page.select_one("a[href*='method=ical']")
    if not link:
        print(f"[IME] No calendar link: {url}")
        return None
    # The listing's JSON-LD has dates only; the iCal export has the times
    found = icalendar.convert_ics_text_to_events(get(session, link["href"]))
    if not found:
        print(f"[IME] No upcoming event in calendar: {url}")
        return None
    event = found[0]
    # The iCal UID is a hash, so let the id come from the url slug
    event.pop("@id", None)
    # CATEGORIES hold internal labels like BIRDSONG and External
    event.pop("keywords", None)
    # The iCal helper takes "Kannada and Hindi poetry" in a bio as the language
    event.pop("inLanguage", None)
    # Without an end on the page, the iCal end is a filler 7 PM; SchemaFixer sets one
    shown = page.select_one(".mec-single-event-time .mec-events-abbr")
    same_day = event["startDate"][:10] == event["endDate"][:10]
    if shown and same_day and START_ONLY.fullmatch(shown.get_text(strip=True)):
        event.pop("endDate")
    event["url"] = url
    event["description"] = SHORTCODE.sub("", event["description"]).strip()
    event["location"] = place(listed.get("location") or {})
    return event


def events():
    session = get_cached_session()
    result = []
    for url, listed in upcoming(get(session, LISTING)):
        try:
            event = make_event(session, url, listed)
        except Exception as e:
            print(f"[IME] Skipping {url}: {type(e).__name__}: {e}")
            continue
        if event:
            result.append(event)
    return result
