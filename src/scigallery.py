from common.session import get_cached_session
import json
import datetime
import re
import os
from urllib.parse import urlencode
from common.tz import IST

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
    "Studio Visit": "EducationEvent",
}

session = get_cached_session()

def guess_event_type(kind):
    # search for each of the keys from the mapper
    # in kind, and pick the first
    for key in event_type_mapper:
        if key in kind:
            return event_type_mapper[key]

    print("[CARBON] Unknown event type: " + kind)
    return "Event"


"""
returns (number_of_days, single_event_duration_in_seconds)
"""


def parse_duration(duration_str):
    # Regular expressions to match hours, minutes, and days
    hour_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*Hours?")
    minute_pattern = re.compile(r"(\d+)\s*Minutes")
    day_pattern = re.compile(r"(\d+)\s*Days")

    # Process hours and minutes otherwise
    hours = sum(float(match) for match in hour_pattern.findall(duration_str))
    minutes = sum(int(match) for match in minute_pattern.findall(duration_str))
    single_event_duration = int((hours * 60 + minutes) * 60)

    days_matches = day_pattern.findall(duration_str)
    if days_matches:
        # If there are days, ignore hours and minutes
        days = sum(int(match) for match in days_matches)
        return (days, single_event_duration)
    else:
        return (0, single_event_duration)


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


def get_location_url(str, venue):
    # assume str contains a a tag, get the href
    matches = re.search(r'href=[\'"]?([^\'" >]+)', str).group(1)
    if matches:
        return matches
    else:
        # search on google maps for venue (urlencode it)
        return "https://www.google.com/maps/search/" + urlencode({"q": venue})


def make_event(e, ts):
    experts = e["experts"].replace("_", " ").title().split(",")
    days, duration = parse_duration(e["duration"])
    if days > 0:
        raise "Event longer than a day not implemented"

    endDate = ts + datetime.timedelta(seconds=duration)
    return {
        "@type": guess_event_type(e["kind"]),
        "name": e["name"].replace("<br>", " ").strip(),
        "location": {
            "@type": "Place",
            "name": e["venue"],
            "address": e["venue"] + ", Bangalore",
            "url": get_location_url(e["location"], e["venue"]),
        },
        "startDate": ts.isoformat(),
        "endDate": endDate.isoformat(),
        "description": e["blurb"],
        "url": "https://carbon.scigalleryblr.org/programmes?"
        + urlencode({"p": e["uid"]}),
        "performer": [
            {"@type": get_performer_type(expert), "name": expert.strip()}
            for expert in experts
        ],
        "maximumAttendeeCapacity": e["capacity"],
    }


def filter_data(data):
    current_time = datetime.datetime.now(IST)
    events = []
    for p in data:
        ts = parse_timestamp(p["timestamp"])
        if ts > current_time:
            events.append(make_event(p, ts))

    return events


def main():
    data = session.get(
        "https://sci560-default-rtdb.firebaseio.com/en/1OR9HC9TgswvCnTgg6tC5pCVIjoc5vV6YlzOe5ijaAzM/programmes.json"
    ).json()
    with open("out/scigalleryblr.json", "w") as f:
        json.dump(filter_data(data), f, indent=2)


if __name__ == "__main__":
    main()
