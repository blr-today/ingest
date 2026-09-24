import re
import json
from ..common import icalendar

CATEGORY_TYPES = {
    "Art Gallery": "ExhibitionEvent",
    "Book Release": "LiteraryEvent",
    "Reading Club": "LiteraryEvent",
    "Lecture": "EducationEvent",
    "Bharata Natyam": "DanceEvent",
    "Carnatic Instrumental": "MusicEvent",
    "Hindusthani Classical": "MusicEvent",
    "Theatre-Play": "TheaterEvent",
}

# "Cultural Programs" is a catch-all, so guess from the (often Kannada) title
NAME_TYPES = [
    (r"music|karaoke|sangeet|gaana|ಸಂಗೀತ", "MusicEvent"),
    (r"dance|natya|ನೃತ್ಯ", "DanceEvent"),
    (r"poetry|kavya|vachana|recit|ವಾಚನ|ಕಾವ್ಯ", "LiteraryEvent"),
    (r"play|drama|nataka|ನಾಟಕ", "TheaterEvent"),
]

ADDRESS = {
    "@type": "PostalAddress",
    "streetAddress": "#6, Shri B P Wadia Road, Basavanagudi",
    "addressLocality": "Bengaluru",
    "addressRegion": "Karnataka",
    "postalCode": "560004",
    "addressCountry": "IN",
}


def get_location(raw_name):
    venue = raw_name.split(",")[0].strip()
    if venue.lower().startswith("indian institute") or venue.lower().startswith(
        "the indian institute"
    ):
        name = "Indian Institute of World Culture, Basavanagudi, Bengaluru"
    else:
        name = f"{venue}, Indian Institute of World Culture, Basavanagudi, Bengaluru"
    return {"@type": "Place", "name": name, "address": ADDRESS}


def modify_event(event):
    for category, etype in CATEGORY_TYPES.items():
        if category in event.get("keywords", []):
            event["@type"] = etype

    if event["@type"] == "Event":
        for pattern, etype in NAME_TYPES:
            if re.search(pattern, event["name"], re.IGNORECASE):
                event["@type"] = etype
                break

    event["location"] = get_location(event["location"]["name"])
    return event


if __name__ == "__main__":
    input_ics_file = "out/iiwc.ics"
    output_json_file = "out/iiwc.json"

    json_data = icalendar.convert_ics_to_events(input_ics_file)
    json_data = [modify_event(event) for event in json_data]

    with open(output_json_file, "w") as output_file:
        output_file.write(json.dumps(json_data, indent=2))

    print(f"[IIWC] {len(json_data)} events")
