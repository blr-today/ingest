import http.client
import json
import re
from bs4 import BeautifulSoup
from requests_cache import CachedSession
from datetime import datetime, timezone, timedelta
import os
from math import ceil

HEADERS = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
}
BASE_URL = "https://www.adidas.co.in/adidasrunners"
COMMUNITY_ID="2e012594-d3fb-4185-b12b-78dead3499a3"
COUNTRY_CODE="IN"

def fetch_events(session):
    events = []
    url = f"{BASE_URL}/ar-api/gw/default/gw-api/v2/events/communities/{COMMUNITY_ID}?countryCodes={COUNTRY_CODE}"
    r = session.get(url, headers=HEADERS).json()
    for data in r['_embedded']['events']:
        location = data['meta']['adidas_runners_locations']
        events.append({
            "name": "Adidas Runners " + data['title'],
            "about": data['description'],
            "url": f"https://www.adidas.co.in/adidasrunners/events/event/{data["id"]}",
            "startDate": data['eventStartDate'],
            "endDate": data['eventStartDate'],
            "image": data['_links']['img']['href'],
            "location": {
                "@type": "Place",
                "name": location,
                "address": location + " Bengaluru",
            }
        })
    return events

def main():
    session = CachedSession(
        "event-fetcher-cache",
        expire_after=timedelta(days=1),
        stale_if_error=True,
        use_cache_dir=True,
        cache_control=False,
    )
    events = fetch_events(session)

    with open("out/adidas.json", "w") as f:
        json.dump(events, f, indent=2)

if __name__ == "__main__":
    main()
