import json
import datetime
from common.session import get_cached_session
from bs4 import BeautifulSoup

"""
Gets extra details from the event page itself
"""
def get_event_details(session, url):
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    txt = soup.find(class_="event-calendar-infotext-container").get_text(strip=True)
    img_src = soup.find(class_="event-calendar-teaser-image").find("img")["src"]
    img_src = f"https://www.goethe.de{img_src}"

    location_name = soup.find(class_="event-calendar-fact-list").find("span").get_text(strip=True)
    location_name = location_name.replace("Bangalore", "").replace(", ", " ").strip()
    location_address = "716, CMH Road, Indiranagar 1st Stage, Bangalore"
    if "Goethe-Institut" not in location_name:
        for line in response.text.splitlines():
            if '"event_location"' in line:
                startIndex = line.index('"event_location":') + len('"event_location":') + 1
                endIndex = line.index('"', startIndex + 1)
                location_address = line[startIndex:endIndex].strip().replace("<br />", " ")

    return {
        "description": txt,
        "image": img_src,
        "location": {
            "@type": "Place",
            "name": location_name,
            "address": location_address
        },
        "offers": {}
    }

def get_event_type(type, subheading):
    MAPPING = {
        "Workshop": "EducationEvent",
        "Session": "EducationEvent",
        "Installation": "ExhibitionEvent",
        "Information": "EducationEvent",
        "Conference": "EducationEvent",
        "Consultation": "EducationEvent",
        "Music": "MusicEvent",
        "Exam": "EducationEvent",
        "Film": "ScreeningEvent",
        "Literary": "LiteraryEvent",
        # These are not an event
        "Call for Applications": None,
    }
    for key, value in MAPPING.items():
        if key.lower() in type.lower() or key.lower() in subheading.lower():
            return value
    return "Event"

def make_event(session, event_dict):
    startTimeText = event_dict["date_start_full"][0:10] + "T" + event_dict["time_start_txt"]
    startTime = datetime.datetime.strptime(startTimeText, "%Y-%m-%dT%I:%M %p")

    if "time_end_txt" in event_dict and event_dict["time_end_txt"] == "":
        endTime   = event_dict["date_start_full"][0:10] + "T" + event_dict["time_end_txt"]
        endTime   = datetime.datetime.strptime(endTime, "%Y-%m-%dT%I:%M %p")
    else:
        endTime = startTime + datetime.timedelta(hours=2)

    details = {
        "name": event_dict["headline"],
        "startDate": event_dict["date_start_full"],
        "location": {
            "name": event_dict["location_IDtxt"]
        },
        "startDate": startTime.isoformat(),
        "endDate": endTime.isoformat(),
        "keywords": ["GOETHE", event_dict.get("subheadline", "")] + [
            category["category_text"] for category in event_dict.get("secondary_categories", [])
        ],
        "@type": get_event_type(event_dict["event_type"], event_dict.get("subheadline", "")),
        "url": f"https://www.goethe.de/ins/in/en/ver.cfm?event_id={event_dict['object_id']}",
    } 
    details |= get_event_details(session, details["url"])

    if event_dict.get("registration_link_url", None):
        details["offers"]["url"] = event_dict["registration_link_url"]
    if event_dict.get("price", None):
        details["offers"]["price"] = event_dict["price"]
        details["offers"]["priceCurrency"] = "INR"
        if event_dict["price"] == "" or event_dict["price"] == 0:
            details['isAccessibleForFree'] = True

    # Too long events are typically courses or announcements
    # could also be installations, but need to investigate for them
    if (endTime - startTime).days > 3:
        print("[GOETHE] Long event dropped:", details["name"])
        details['type'] = None

    return details

def fetch_events():
    events = []
    session = get_cached_session()
    payload = {
        "langId": "1",
        "filterData": json.dumps(
            {
                "adress_IDtxt": "Bangalore",
                "dateStart": datetime.datetime.now().strftime("%d-%m-%Y"),
                "dateEnd": (
                    datetime.datetime.now() + datetime.timedelta(days=60)
                ).strftime("%d-%m-%Y"),
            }
        ),
    }

    response = session.get(
        "https://www.goethe.de/rest/objeventcalendarRedesign/events/fetchEvents", params=payload
    )

    for event in response.json()["eventItems"]:
        details = make_event(session, event)
        if details['@type'] != None:
            events.append(details)
    return events

if __name__ == "__main__":
    events = fetch_events()
    # Write output JSON file
    with open("out/goethe.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
        print(f"[GOETHE] {len(events)} events")

