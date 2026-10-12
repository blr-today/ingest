import logging
import re

from bs4 import BeautifulSoup

from src.common.session import get_cached_session

from .base import Processor
from .cost import as_keywords

API = "https://courtyardkoota.com/wp-json/wp/v2/ajde_events"
# event_type-* class suffix -> (schema.org type, keywords)
TYPES = {
    "food": ("FoodEvent", []),
    "comedy": ("ComedyEvent", []),
    "stand-up-comedy": ("ComedyEvent", []),
    "dance": ("DanceEvent", ["Dance"]),
    "dance-theatre": ("DanceEvent", ["Dance"]),
    "film": ("ScreeningEvent", []),
    "music": ("MusicEvent", ["Music"]),
    "play": ("TheaterEvent", []),
    "theatre": ("TheaterEvent", []),
    "poetry": ("LiteraryEvent", []),
    "stories": ("LiteraryEvent", []),
    "book-talk": ("LiteraryEvent", []),
    "workshop": ("EducationEvent", []),
    "talk": ("EducationEvent", ["Talks"]),
    "exhibition": ("VisualArtsEvent", []),
    "games": ("SocialEvent", []),
}


def plain_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["p", "br", "li", "div", "h1", "h2", "h3", "h4"]):
        tag.append("\n")
    text = soup.get_text()
    lines = (re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def fetch_record(url):
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    try:
        response = get_cached_session().get(API, params={"slug": slug}, timeout=30)
        response.raise_for_status()
        records = response.json()
    except Exception as e:
        logging.warning("Koota REST lookup failed for %s: %s", url, e)
        return None
    return records[0] if records else None


def apply_record(event, record):
    description = plain_text(record.get("content", {}).get("rendered", ""))
    if description:
        event["description"] = description
    prefix = "event_type-"
    slugs = [c[len(prefix):] for c in record.get("class_list", []) if c.startswith(prefix)]
    known = [TYPES[s] for s in slugs if s in TYPES]
    if known:
        if event.get("@type") in (None, "Event"):
            event["@type"] = known[0][0]
        extra = [k for _, tags in known for k in tags]
        event["keywords"] = list(dict.fromkeys(as_keywords(event.get("keywords")) + extra))


class Koota(Processor):
    # Fix dates before SchemaFixer parses them
    URL_REGEX = r"^https?://(www\.)?courtyardkoota\.com/"

    @staticmethod
    def process(url, event):
        record = fetch_record(url)
        if record:
            apply_record(event, record)

        for x in ["startDate", "endDate"]:
            if x in event:
                # HACK: This is specific to Courtyard Koota
                # where dates are not in ISO format
                event[x] = event[x].replace("+5.5:00", "+05:30")
                time = year = None
                if "T" in event[x]:
                    date, time = event[x].split("T")
                    year, month, day = date.split("-")
                else:
                    yy = event[x].split("-")
                    if len(yy) == 3:
                        year, month, day = yy
                if year:
                    month = month.zfill(2)
                    day = day.zfill(2)
                    event[x] = f"{year}-{month}-{day}"
                    if time:
                        event[x] = f"{event[x]}T{time}"

        return event
