import json
from bs4 import BeautifulSoup
from datetime import datetime
from ..common.fetch import Fetch
from ..common.tz import IST

URL = "https://blrbirders.com/"

fetcher = Fetch(browser="chrome")


def fetch_event_location(url):
    response = fetcher.get(url=url)
    soup = BeautifulSoup(response.text, "html.parser")
    location = soup.select_one(".evo_location_name").text.strip()
    loc = soup.select_one(".evcal_location").get("data-latlng")

    if loc:
        lat, lng = loc.split(",")
        return (location, lat, lng)
    return (location, None, None)


def parse_bng_bird_events(soup):
    events = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            if tag.string.endswith("})()"):
                tag.string += '"}'
            event = json.loads(tag.string)
        except:
            print("[BLRBIRDERS] Failed to parse " + tag.string.split("\n")[1])
        # https://blrbirders.com/events/first-sunday-bird-walk/var/ri-16.l-L1 -> https://blrbirders.com/events/first-sunday-bird-walk/

        event['url'] = event['url'].split("/var/")[0]

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
        event["@id"] = "com.blrbirders:" + event["@id"]
        location, lat, lng = fetch_event_location(event["url"])
        event["location"] = {
            "name": location,
            "@type": "Place",
            
        }
        if lat:
            event['location']["geo"] =  {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng}

        if "organizer" in event:
            del event["organizer"]
        events.append(event)

    return events


if __name__ == "__main__":
    response = fetcher.get(url=URL)
    soup = BeautifulSoup(response.text, "html.parser")

    events = parse_bng_bird_events(soup)

    with open("out/blrbirders.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
        print(f"[BNGBIRDS] {len(events)} events")
