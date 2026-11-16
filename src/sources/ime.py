import re
from datetime import datetime

from bs4 import BeautifulSoup

from ..common import USER_AGENT_HEADERS, icalendar
from ..common.jsonld import JsonLdExtractor
from ..common.session import get_cached_session
from ..common.tz import IST

BASE = "https://indianmusicexperience.org/"
LISTING = BASE + "events/"
# The listing's JSON-LD has dates only; each event's iCal export has the times
ICAL_LINK = re.compile(r"\?method=ical&(?:amp;|#038;)?id=(\d+)")
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
    return session.get(url, headers=USER_AGENT_HEADERS, timeout=30).text


def upcoming(page):
    today = datetime.now(IST).date().isoformat()
    for item in JsonLdExtractor().extract(page):
        if item.get("@type") != "Event":
            continue
        url = (item.get("offers") or {}).get("url")
        if not url:
            print(f"[IME] No url for {item.get('name')}")
        elif (item.get("endDate") or item.get("startDate") or "") >= today:
            yield url, item


def place(listed):
    # Museum events leave the place blank or name it "IME Museum"
    if not isinstance(listed, dict) or listed.get("name", "").strip() in ("", "IME Museum"):
        return MUSEUM
    return {"@type": "Place", "name": listed["name"].strip(), "address": listed.get("address", "")}


def make_event(session, url, listed):
    page = get(session, url)
    match = ICAL_LINK.search(page)
    if not match:
        print(f"[IME] No calendar link: {url}")
        return None
    found = icalendar.convert_ics_text_to_events(get(session, f"{BASE}?method=ical&id={match[1]}"))
    if not found:
        return None
    event = found[0]
    # The iCal UID is a hash, so let the id come from the url slug
    event.pop("@id", None)
    # CATEGORIES hold internal labels like BIRDSONG and External
    event.pop("keywords", None)
    # Bios mention languages, so leave the guess to the languages processor
    event.pop("inLanguage", None)
    # Without an end on the page, the iCal end is a filler 7 PM; SchemaFixer sets one
    shown = BeautifulSoup(page, "html.parser").select_one(".mec-single-event-time .mec-events-abbr")
    if shown and START_ONLY.fullmatch(shown.get_text(strip=True)):
        event.pop("endDate", None)
    event["url"] = url
    event["description"] = SHORTCODE.sub("", event["description"]).strip()
    event["location"] = place(listed.get("location"))
    return event


def events():
    session = get_cached_session()
    return [
        event
        for url, listed in upcoming(get(session, LISTING))
        if (event := make_event(session, url, listed))
    ]
