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
        return records[0] if records else None
    except Exception as e:
        logging.warning("Koota REST lookup failed for %s: %s", url, e)
        return None


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
            if not isinstance(event.get(x), str):
                continue
            # HACK: Courtyard Koota dates are not in ISO format; SchemaFixer flags the rest
            value = event[x].replace("+5.5:00", "+05:30")
            date, _, time = value.partition("T")
            parts = date.split("-")
            if len(parts) == 3 and parts[0]:
                year, month, day = parts
                value = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                value += f"T{time}" if time else ""
            event[x] = value

        return event
