import requests
import json
import datetime
from urllib.parse import urlencode
from common.tz import IST

# Each season gets a new subdomain and Firebase DB (see the season's script.js)
SEASON = "quantum"
SEASON_DB_HOST = "https://quantum-7bdd1-default-rtdb.asia-southeast1.firebasedatabase.app"
SEASON_SITE = f"https://{SEASON}.scigalleryblr.org"

event_type_mapper = {
    "Film": "ScreeningEvent",
    "Lecture": "EducationEvent",
    "AMA": "EducationEvent",
    "Tutorial": "EducationEvent",
    "Masterclass": "EducationEvent",
    "Performance": "VisualArtsEvent",
    "Workshop": "EducationEvent",
    "Event": "Event",
    "Walkthrough": "EducationEvent",
    "Walk": "EducationEvent",
    "Studio Visit": "EducationEvent",
    "Artist Talk": "EducationEvent",
    "Lab Visit": "EducationEvent",
    "Quiz": "EducationEvent",
    "Panel Discussion": "EducationEvent",
    "Game On": "EducationEvent",
    "Co-Craft": "EducationEvent",
    "Co-Draw": "EducationEvent",
    "Co-Read": "EducationEvent",
}


def guess_event_type(kind):
    # search for each of the keys from the mapper
    # in kind, and pick the first
    for key in event_type_mapper:
        if key in kind:
            return event_type_mapper[key]

    print("[SCIGALLERY] Unknown event type: " + kind)
    return "Event"


def parse_duration_hours(duration_str):
    # duration is a plain number of hours, e.g. "1.5"
    try:
        return float(duration_str)
    except (TypeError, ValueError):
        return 0.0


def get_performer_type(expert):
    e = expert.lower()
    if "festival" in e or "foundation" in e:
        return "Organization"
    else:
        return "Person"


def parse_timestamp(timestamp: str):
    try:
        return datetime.datetime.fromisoformat(timestamp).astimezone(IST)
    # Return a very old date so this event is ignored
    except:
        return datetime.datetime(1900, 1, 1, tzinfo=IST)


def make_event(e, ts, experts):
    endDate = ts + datetime.timedelta(hours=parse_duration_hours(e["duration"]))

    is_offsite = e.get("offsite") == "true"
    location = {
        "@type": "Place",
        "name": e.get("venue") or "Science Gallery Bengaluru",
        "address": "Bangalore" if is_offsite else "Science Gallery, Bangalore",
    }
    if e.get("location"):
        location["url"] = e["location"]

    performer = [
        {
            "@type": get_performer_type(experts[eid]["name"]),
            "name": experts[eid]["name"],
        }
        for eid in e["experts"].split(",")
        if eid.strip() and eid.strip() in experts
    ]

    event = {
        "@type": guess_event_type(e["kind"]),
        "name": e["name"].replace("<br>", " ").strip(),
        "location": location,
        "startDate": ts.isoformat(),
        "endDate": endDate.isoformat(),
        "description": e["blurb"],
        "url": SEASON_SITE + "/programmes?" + urlencode({"p": e["slug"]}),
        "isAccessibleForFree": True,
        "maximumAttendeeCapacity": e["capacity"],
    }
    if e.get("image"):
        event["image"] = e["image"]
    if performer:
        event["performer"] = performer

    return event


def filter_data(data, experts):
    current_time = datetime.datetime.now(IST)
    events = []
    for p in data:
        ts = parse_timestamp(p["timestamp"])
        if ts > current_time and p["hide"] == "true":
            events.append(make_event(p, ts, experts))

    return events


def main():
    data = requests.get(
        f"{SEASON_DB_HOST}/{SEASON}/en/programmes.json"
    ).json().values()
    experts = requests.get(f"{SEASON_DB_HOST}/{SEASON}/en/experts.json").json() or {}
    with open("out/scigalleryblr.json", "w") as f:
        json.dump(filter_data(data, experts), f, indent=2)


if __name__ == "__main__":
    main()
