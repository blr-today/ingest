import ics
import re
import datetime
from datetime import timedelta
from .tz import IST

LANGUAGE_MAP = {
    "Hindi": "hi",
    "Kannada": "kn",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Marathi": "mr",
    "Bengali": "bn",
    "Gujarati": "gu",
    "Punjabi": "pa",
    "Odia": "or",
    "Assamese": "as",
    "Urdu": "ur",
    # Unlikely to have an event in sanskrit
    # "Sanskrit": "sa",
    "Nepali": "ne",
    "Sindhi": "sd",
}


def convert_ics_to_events(ics_file_path):
    events = []

    with open(ics_file_path, "r") as file:
        calendar = ics.Calendar(file.read())

    for event in calendar.events:
        if event.end == event.begin:
            event.end = event.begin + timedelta(hours=2)
        event_json = {
            "@context": "https://schema.org",
            "@type": "Event",
            "@id": event.uid,
            "name": event.name,
            "startDate": event.begin.astimezone(IST).isoformat(),
            "endDate": event.end.astimezone(IST).isoformat(),
            "description": event.description or "",
            "url": event.url,
        }
        # if endDate is in the past, continue
        if event.end.astimezone(IST) < datetime.datetime.now(IST):
            continue

        if len(event.categories) > 0:
            event_json["keywords"] = sorted(event.categories)

        if event.location:
            event_json["location"] = {"@type": "Place", "name": event.location}

        for l in LANGUAGE_MAP:
            regex = r"\b" + l + r"\b"
            if re.search(regex, event_json["description"]):
                event_json["inLanguage"] = LANGUAGE_MAP[l]

        if "inLanguage" not in event_json:
            event_json["inLanguage"] = "en"

        # Film Screenings is for MAP
        if (
            re.search(r"\bsubtitles", event_json["description"], re.IGNORECASE)
            or "Film Screenings" in event.categories
        ):
            event_json["@type"] = "ScreeningEvent"
            event_json["workPresented"] = {
                "@type": "Movie",
                "name": event.name,
            }

            L_WITH_ENGLISH = LANGUAGE_MAP | {"English": "en"}
            for l in L_WITH_ENGLISH:
                if re.search(
                    r"\b" + l + r" subtitles\b",
                    event_json["description"],
                    re.IGNORECASE,
                ):
                    event_json["subtitleLanguage"] = L_WITH_ENGLISH[l]

        # MAP SPECIFIC
        if "Workshops" in event.categories:
            event_json["@type"] = "EducationEvent"
        if "Performances" in event.categories and "music" in event_json["description"]:
            event_json["@type"] = "MusicEvent"
        elif "Performances" in event.categories:
            event_json["@type"] = "TheaterEvent"

        if "Performing Arts" in event.categories and "Theatre" in event.categories:
            event_json["@type"] = "TheaterEvent"
            event_json["workPerformed"] = {
                "@type": "TheaterPlay",
                "name": event.name,
            }

        if "Performing Arts" in event.categories and "Music" in event.categories:
            event_json["@type"] = "MusicEvent"
            event_json["workPerformed"] = {
                "@type": "CreativeWork",
                "name": event.name,
            }

        # Check for attachments (if image)
        if event.extra:
            for line in event.extra:
                if line.name == "ATTACH" and line.value.startswith("https"):
                    event_json["image"] = line.value
                    break

        events.append(event_json)

    return events
