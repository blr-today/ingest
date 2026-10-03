import re

from .base import Processor
from .cost import as_keywords

# The first match is the type, so narrower types sit above broader ones
RULES = [
    ("ChildrensEvent", r"\bkids?\b|\bchildren|\bplaydate", []),
    ("ScreeningEvent", r"\bscreening", []),
    ("TheaterEvent", r"\bplay\b|\btheat(re|er)\b|\bpuppet|\bimprov\b", []),
    (
        "LiteraryEvent",
        r"\bbook (launch|club|reading)|\breading\b|\bpoetry\b|(?<!long )\bstory\b",
        [],
    ),
    ("ComedyEvent", r"\broast\b|\bcomedy\b|\bstand-?up\b", []),
    (
        "BusinessEvent",
        r"\bstartups?\b|\bfounders?'?s? (room|pitch|meetup)|\bnetworking\b",
        [],
    ),
    (
        "FoodEvent",
        r"\btasting\b|\bdinner\b|\blunch\b|\bbrunch\b|\bmatcha\b|\bpastr(y|ies)\b"
        r"|\bmixology\b|\bcocktail (making|workshop|masterclass|class)\b"
        r"|\bbak(e|ing)\b|\bcooking\b|\bchocolate"
        r"|\bkombucha\b|\bsushi\b|\bpasta\b|\bbread\b|\bdim ?sum\b|\bcheese\b"
        r"|\bcakes?\b|\b(coffee|beer) brewing\b|\bbrewing (workshop|class)\b"
        r"|\bcupping\b",
        [],
    ),
    (
        "EducationEvent",
        r"\bworkshop|\bmasterclass|\bclass\b|\bcourse\b|\blearn\b"
        r"|\b(a|the) talk\b|\btalk (on|by)\b|\bdiy\b|\bmaking\b",
        ["Talks"],
    ),
    ("VisualArtsEvent", r"\bsketch", []),
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
# Without a telling name, descriptions name the format before categories do
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
        keywords = set(as_keywords(event.get("keywords")))
        kinds = [k for k, pattern, _ in RULES if re.search(pattern, name)]
        kinds = kinds or [
            next((k for k, p in DESCRIPTIONS if re.search(p, description)), None)
            or next((k for k, _, tags in RULES if keywords & set(tags)), None)
        ]
        if kinds[0]:
            event["@type"] = kinds[0]
        # Pages read @type as one string, so the other matches go here
        if len(kinds) > 1:
            event["additionalType"] = [f"https://schema.org/{k}" for k in kinds[1:]]
        return event
