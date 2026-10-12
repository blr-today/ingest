import json
from datetime import datetime
from ..common import icalendar

LOCATION = {
    "@type": "Place",
    "name": "Alliance Française de Bangalore",
    "address": "Thimmaiah Rd, Kaverappa Layout, Vasanth Nagar, Bengaluru, Karnataka 560001",
    "geo": {
        "@type": "GeoCoordinates",
        "latitude": "12.99146",
        "longitude": "77.59685",
    },
}

CATEGORY_TYPES = {
    "Film": "ScreeningEvent",
    "Cinema": "ScreeningEvent",
    "Concert": "MusicEvent",
    "Exhibition": "ExhibitionEvent",
    "Workshops": "EducationEvent",
    "Talks": "EducationEvent",
}


def modify_event(event):
    for category, etype in CATEGORY_TYPES.items():
        if any(category.lower() in k.lower() for k in event.get("keywords", [])):
            event["@type"] = etype
            break
    event["location"] = LOCATION
    return event


def is_short(event):
    start = datetime.fromisoformat(event["startDate"])
    end = datetime.fromisoformat(event["endDate"])
    return (end - start).days <= 3


if __name__ == "__main__":
    events = icalendar.convert_ics_to_events("out/afbangalore.ics")
    # Longer events are courses such as the weekly French Choir
    events = [modify_event(e) for e in events if is_short(e)]

    with open("out/afbangalore.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f"[AFBANGALORE] {len(events)} events")
