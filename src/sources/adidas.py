import json
import curl_cffi
from datetime import datetime
import asyncio
from src.common.tz import IST

BASE_URL = "https://www.adidas.co.in/adidasrunners"
COMMUNITY_ID = "2e012594-d3fb-4185-b12b-78dead3499a3"
COUNTRY_CODE = "IN"
BROWSER_CODE = "safari184_ios"
# custom User-Agent trips the WAF when it mismatches the impersonated TLS fingerprint

def _date(date_str):
    return datetime.fromisoformat(date_str).astimezone(IST).isoformat()


def _description(data):
    lines = [data["description"].strip()]
    if distance := data["meta"].get("distanceInM"):
        lines.append(f"Distance: {distance / 1000:g} km")
    return "\n".join(lines)


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
                "description": _description(data),
                "url": f"https://www.adidas.co.in/adidasrunners/events/event/{_id}",
                "startDate": _date(data["eventStartDate"]),
                "endDate": _date(data["eventEndDate"]),
                "image": data["_links"]["img"]["href"],
                "location": {
                    "@type": "Place",
                    "name": location,
                    "address": location + " Bengaluru",
                },
            }
        )
    return events


def events():
    return fetch_events()
