import http.client
import json
import datetime
import re
import os

event_type_mapper = {
    "Film": "ScreeningEvent",
    "Lecture": "EducationEvent",
    "Tutorial": "EducationEvent",
    "Masterclass": "EducationEvent",
    "Performance": "VisualArtsEvent",
    "Workshop": "EducationEvent"
}

def guess_event_type(kind):
    # search for each of the keys from the mapper
    # in kind, and pick the first
    for key in event_type_mapper:
        if key in kind:
            return event_type_mapper[key]

    return "Event"

tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))  # Asia/Kolkata timezone

def fetch_data(host, path):
    conn = http.client.HTTPSConnection(host)
    conn.request("GET", path)
    data = conn.getresponse().read()
    conn.close()
    return data

def parse_duration(duration_str):
    # Regular expressions to match hours, minutes, and days
    hour_pattern = re.compile(r"(\d+(?:\.\d+)?)\s*Hours?")
    minute_pattern = re.compile(r"(\d+)\s*Minutes")
    day_pattern = re.compile(r"(\d+)\s*Days")

    # Find all matches
    days_matches = day_pattern.findall(duration_str)
    if days_matches:
        # If there are days, ignore hours and minutes
        days = sum(int(match) for match in days_matches)
        return f"P{days}D"

    # Process hours and minutes otherwise
    hours = sum(float(match) for match in hour_pattern.findall(duration_str))
    minutes = sum(int(match) for match in minute_pattern.findall(duration_str))

    # Convert fractional hours to hours + minutes
    additional_hours, fractional_hours = divmod(hours, 1)
    minutes += fractional_hours * 60
    hours = int(additional_hours)

    # Convert minutes to hours if 60 or more
    hours += int(minutes // 60)
    minutes = int(minutes % 60)

    # Construct ISO8601 duration string
    iso_duration = "P"
    if hours or minutes:
        iso_duration += "T"
    if hours:
        iso_duration += f"{hours}H"
    if minutes:
        iso_duration += f"{minutes}M"
    return iso_duration if iso_duration != "P" else "PT0M" # Handle case with no duration

def parse_timestamp(timestamp):
    try:
        return datetime.datetime.fromisoformat(timestamp).astimezone(tz)
    # Return a very old date so this event is ignored
    except:
        return datetime.datetime(1900, 1, 1, tzinfo=tz)

def make_event(e, ts):
  experts = e["experts"].replace("_", " ").title().split(",")
  return {
    "@context": "http://schema.org",
    "@type": guess_event_type(e["kind"]),
    "name": e["name"],
    "location": e["venue"],
    "startDate": ts.isoformat(),
    "description": e["blurb"],
    "duration": parse_duration(e["duration"]),
    "url": "https://carbon.scigalleryblr.org/programmes?p=" + e["uid"],
    "performer": [{"@type": "Person", "name": expert} for expert in experts],
    "maximumAttendeeCapacity": e["capacity"],
    "organizer": {
        "@type": "Organization",
        "name": "Science Gallery Bengaluru",
        "url": "https://carbon.scigalleryblr.org"
    }
  }

def filter_data(data):
    current_time = datetime.datetime.now(tz)
    events = []
    for p in data:
        ts = parse_timestamp(p["timestamp"])
        if ts > current_time:
            events.append(make_event(p, ts))

    return events

def save_data(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    events = json.loads(fetch_data("carbon-50388-default-rtdb.firebaseio.com", "/en/1ZJfGJT-7ZTOZoevdZZmh2hwXd2935ffJoWee9XXyFZ4/programmes.json"))
    filtered_events = filter_data(events)
    save_data(filtered_events, "out/scigalleryblr.json")

if __name__ == "__main__":
    main()
