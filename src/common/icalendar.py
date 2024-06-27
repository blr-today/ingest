import ics
import re

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
    "Sanskrit": "sa",
    "Nepali": "ne",
    "Sindhi": "sd"
}

def convert_ics_to_events(ics_file_path):
    events = []

    with open(ics_file_path, 'r') as file:
        calendar = ics.Calendar(file.read())

    for event in calendar.events:
        event_json = {
            "@context": "http://schema.org",
            "@type": "Event",
            "name": event.name,
            "startDate": event.begin.isoformat(),
            "endDate": event.end.isoformat(),
            "description": event.description,
            "url": event.url
        }

        if len(event.categories) > 0:
            event_json['keywords'] = ", ".join(sorted(event.categories)),

        if event.location:
            event_json['location'] = {
                "@type": "Place",
                "name": event.location
            }

        for l in LANGUAGE_MAP:
            regex = r"\b" + l + r"\b"
            if re.search(regex, event_json['description']):
                event_json['inLanguage'] = LANGUAGE_MAP[l]

        if 'inLanguage' not in event_json:
            event_json['inLanguage'] = "en"

        if re.search(r"\bsubtitles", event_json['description'], re.IGNORECASE):
            event_json['@type'] = "ScreeningEvent"
            event_json['workPresented'] = {
                "@type": "Movie",
                "name": event.name,
            }
            
            L_WITH_ENGLISH = LANGUAGE_MAP  | {"English": "en"}
            for l in L_WITH_ENGLISH:
                if re.search(r"\b" + l + r" subtitles\b", event_json['description'], re.IGNORECASE):
                    event_json['subtitleLanguage'] = L_WITH_ENGLISH[l]

        if 'Performing Arts' in event.categories and 'Theatre' in event.categories:
            event_json['@type'] = "TheaterEvent"
            event_json['workPerformed'] = {
                "@type": "TheaterPlay",
                "name": event.name,
            }

        if 'Performing Arts' in event.categories and 'Music' in event.categories:
            event_json['@type'] = "MusicEvent"
            event_json['workPerformed'] = {
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