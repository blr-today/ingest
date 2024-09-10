import yaml
import json
from datetime import timedelta, datetime
from common.tz import IST
from common.session import get_cached_session
from bs4 import BeautifulSoup
from math import ceil


def get_description(session, url):
    soup = BeautifulSoup(session.get(url).content, "html.parser")
    desc = ""
    for e in soup.select(".rlr-readmore-desc__content"):
        if "Lorem" not in e.text and "Dolor" not in e.text:
            desc += e.text

    return desc


def get_calendar(session, tour_id):
    start_date = (datetime.now().strftime("%Y-%m-%d"),)
    end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    url = f"https://gullytours.vacationlabs.com/itineraries/trips/{tour_id}/departure_calendar.json"

    querystring = {
        "start": start_date,
        "end": end_date,
    }
    d = session.get(url, params=querystring).json()
    keys = d["departure_calendar"]["availability_keys"]
    c = d["departure_calendar"]["availability"]["data"]
    for date in c:
        for x in c[date].values():
            for trip in x:
                trip_details = dict(zip(keys, trip))
                price = d["departure_calendar"]["pricings"][
                    str(trip_details["pricing_group_id"])
                ]["sticker_price"]
                trip_details["price"] = str(ceil(price))
                del trip_details["pricing_group_id"]
                yield trip_details


def main():
    session = get_cached_session()

    events = []
    for tour in read_config():
        description = get_description(session, tour["url"])
        for trip in get_calendar(session, tour["id"]):
            events.append(make_event(tour, description, trip))

    with open("out/gullytours.json", "w") as f:
        json.dump(events, f, indent=2)
        print(f"[GULLYTOURS] {len(events)} events")


def make_event(tour, description, trip):
    start_time = datetime.fromisoformat(trip["starts_at"]).replace(tzinfo=IST)
    end_time = datetime.fromisoformat(trip["ends_at"]).replace(tzinfo=IST)
    event = {
        "@context": "https://schema.org",
        "url": tour["url"],
        "@type": "SocialEvent",
        "name": tour.get("name"),
        "description": description,
        "startDate": start_time.isoformat(),
        "endDate": end_time.isoformat(),
        "eventAttendanceMode": "OfflineEventAttendanceMode",
        "maximumAttendeeCapacity": trip["total_capacity"],
        "remainingAttendeeCapacity": trip["available_seats"],
        # "image": trip['image'],
        "offers": [
            {
                "@type": "Offer",
                "price": trip["price"],
                "priceCurrency": "INR",
            }
        ],
        "organizer": {"@type": "Organization", "name": "Gully Tours"},
        "keywords": ["GULLYTOURS"],
        # "location": {
        #     "@type": "Place",
        #     "name": trip['location'],
        #     "address": trip['location'] + " Bengaluru",
        # }
    }
    return event


def read_config():
    return yaml.safe_load(open("in/known-hosts.yml"))["gullytours"]


if __name__ == "__main__":
    main()
