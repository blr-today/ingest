import json
from common.session import get_cached_session
from bs4 import BeautifulSoup
from common.tz import IST
from datetime import datetime

URL = "https://bngbirds.com/"


def fetch_event_location(url):
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    location = soup.select_one(".evo_location_name").text.strip()
    lat, lng = soup.select_one(".evcal_location").get("data-latlng").split(",")
    return (location, lat, lng)


def parse_bng_bird_events(soup):
    events = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            if tag.string.endswith("})()"):
                tag.string += '"}'
            event = json.loads(tag.string)
        except:
            print("[BNGBIRDS] Failed to parse " + tag.string.split("\n")[1])

        event["startDate"] = (
            datetime.strptime(event["startDate"], "%Y-%m-%dT%H:%M+5.5:00")
            .replace(tzinfo=IST)
            .isoformat()
        )
        event["endDate"] = (
            datetime.strptime(event["endDate"], "%Y-%m-%dT%H:%M+5.5:00")
            .replace(tzinfo=IST)
            .isoformat()
        )
        event["description"] = (
            BeautifulSoup(event["description"], "html.parser")
            .text.replace(" ", "\n")
            .replace("Meeting time", "\nMeeting time")
            .strip()
        )
        event["@id"] = "com.bngbirds:" + event["@id"]
        location, lat, lng = fetch_event_location(event["url"])
        event["location"] = {
            "name": location,
            "@type": "Place",
            "geo": {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng},
        }

        if "organizer" in event:
            del event["organizer"]
        events.append(event)

    return events


if __name__ == "__main__":
    session = get_cached_session()
    response = session.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")

    events = parse_bng_bird_events(soup)

    # Write output JSON file
    with open("out/bngbirds.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
        print(f"[BNGBIRDS] {len(events)} events")
