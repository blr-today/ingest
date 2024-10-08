import json
from datetime import datetime
from curl_cffi import requests
from common.tz import IST

BASE_URL = "https://www.adidas.co.in/adidasrunners"
COMMUNITY_ID = "2e012594-d3fb-4185-b12b-78dead3499a3"
COUNTRY_CODE = "IN"


def _date(date_str):
    return datetime.fromisoformat(date_str).astimezone(IST).isoformat()


def fetch_events(session):
    events = []
    url = f"{BASE_URL}/ar-api/gw/default/gw-api/v2/events/communities/{COMMUNITY_ID}?countryCodes={COUNTRY_CODE}"
    res = session.get(url, impersonate="chrome").json()
    for data in res["_embedded"]["events"]:
        location = data["meta"]["adidas_runners_locations"]
        _id = data["id"]
        events.append(
            {
                "name": "Adidas Runners " + data["title"],
                "about": data["description"],
                "url": f"https://www.adidas.co.in/adidasrunners/events/event/{_id}",
                "startDate": _date(data["eventStartDate"]),
                "endDate": _date(data["eventStartDate"]),
                "image": data["_links"]["img"]["href"],
                "location": {
                    "@type": "Place",
                    "name": location,
                    "address": location + " Bengaluru",
                },
            }
        )
    return events


def main():
    session = requests.Session()
    r = session.get(f"{BASE_URL}/community/bengaluru", impersonate="chrome")
    if len(r.cookies) == 0:
        print("Failed to fetch cookies for Adidas")
        sys.exit(1)
    events = fetch_events(session)

    with open("out/adidas.json", "w") as f:
        json.dump(events, f, indent=2)


if __name__ == "__main__":
    main()
