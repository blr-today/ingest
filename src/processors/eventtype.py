import re

from .base import Processor
from .cost import as_keywords

# First match wins, so narrower types sit above broader ones
RULES = [
    ("ChildrensEvent", r"\bkids?\b|\bchildren|\bplaydate", []),
    ("ScreeningEvent", r"\bscreening", []),
    ("TheaterEvent", r"\bplay\b|\btheat(re|er)\b|\bpuppet|\bimprov\b", []),
    (
        "LiteraryEvent",
        r"\bbook (launch|club|reading)|\breading\b|\bpoetry\b|\bstory\b",
        [],
    ),
    ("ComedyEvent", r"\broast\b|\bcomedy\b|\bstand-?up\b", []),
    ("BusinessEvent", r"\bstartups?\b|\bfounders?\b|\bnetworking\b", []),
    (
        "EducationEvent",
        r"\bworkshop|\bmasterclass|\bclass\b|\bcourse\b|\blearn\b|\btalk\b"
        r"|\bdiy\b|\bmaking\b",
        ["Talks"],
    ),
    ("VisualArtsEvent", r"\bsketch", []),
    ("FoodEvent", r"\btasting\b|\bdinner\b|\blunch\b|\bbrunch\b", []),
    ("DanceEvent", r"\bdance\b", ["Dance"]),
    (
        "MusicEvent",
        r"\bdj\b|\btribute\b|\bconcert\b|\bgig\b|\bvinyl\b|\brap\b|\bfunk\b",
        ["Music", "Live GIG"],
    ),
    ("SportsEvent", r"\byoga\b|\bpilates\b|\bpadel\b|\bcalisthenics\b", ["Active"]),
    (
        "SocialEvent",
        r"\btrivia\b|\bquiz|\bboard games?\b|\btabletop\b|\bchess\b"
        r"|\bmeet-?up\b|\bopen mic\b|\bcraft night\b",
        [],
    ),
]
# Descriptions name the format, and a talk about music is still a talk
DESCRIPTIONS = [
    (
        "EducationEvent",
        r"\b(this|a) ([\w-]+ )?(talk|lecture|workshop|panel discussion)\b",
    ),
    ("MusicEvent", r"\bthis concert\b"),
]


class EventType(Processor):
    PRIORITY = 800

    @staticmethod
    def process(url, event):
        if event.get("@type") not in (None, "Event"):
            return event
        name = str(event.get("name") or "").lower()
        description = str(event.get("description") or "").lower()
        for kind, pattern in DESCRIPTIONS:
            if re.search(pattern, description):
                event["@type"] = kind
                return event
        keywords = set(as_keywords(event.get("keywords")))
        for kind, pattern, tags in RULES:
            if re.search(pattern, name) or keywords & set(tags):
                event["@type"] = kind
                break
        return event
