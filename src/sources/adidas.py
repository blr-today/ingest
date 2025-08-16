import json
import curl_cffi
from datetime import datetime
import asyncio
from common.tz import IST

BASE_URL = "https://www.adidas.co.in/adidasrunners"
COMMUNITY_ID = "2e012594-d3fb-4185-b12b-78dead3499a3"
COUNTRY_CODE = "IN"
BROWSER_CODE = "safari18_4_ios"

def _date(date_str):
    return datetime.fromisoformat(date_str).astimezone(IST).isoformat()


def fetch_events():
    events = []
    url = f"{BASE_URL}/ar-api/gw/default/gw-api/v2/events/communities/{COMMUNITY_ID}?countryCodes={COUNTRY_CODE}"
    body = curl_cffi.get(url, impersonate=BROWSER_CODE).content
    res = json.loads(body)
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
    with open("out/adidas.json", "w") as f:
        events = fetch_events()
        print(f"[ADIDAS] {len(events)} events")
        json.dump(events, f, indent=2)


if __name__ == "__main__":
    main()
