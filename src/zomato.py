import sys
import jsonpath
import re
import json
from urllib.parse import urlparse, parse_qs
from common.fetch import Fetch
import datetime
from common.tz import IST
from common import USER_AGENT_HEADERS
import os

EVENT_URL_REGEX = r"(https:\/\/www\.zomato\.com\/events\/[\w|-]+-et\d+)"

# Public Key, not-logged-in API key
ZOMATO_API_KEY = os.environ.get("ZOMATO_PUBLIC_API_KEY")
BASE_URL = "https://zoma.to/live-event/"
KNOWN_BAD_EVENTS = [
    "43612", # SkyJumper Trampoline Park, too long
    "44864", # Wonderla Amusement Park
]


def fix_date(date_str):
    return datetime.datetime.fromisoformat(date_str).replace(tzinfo=IST)


def get_events(session, event_id):
    if event_id in KNOWN_BAD_EVENTS:
        return
    url = f"{BASE_URL}{event_id}"
    session.browser = "chrome"
    r = session.get(url, cache=True)
    # search for event_url_regex in r.text
    if re.search(EVENT_URL_REGEX, r.text):
        event_url = re.search(EVENT_URL_REGEX, r.text).group(1)
        r = session.get(event_url, cache=True)
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(r.text, "html.parser")
    scripts = soup.find_all("script")
    found = False
    for script in scripts:
        if "__PRELOADED_STATE__" in script.text:
            found = True
            preloaded_state = script.text.strip()
            start = preloaded_state.find("JSON.parse(") + len("JSON.parse(")
            d = json.loads(preloaded_state[start:-2])
            page_data = json.loads(d)
            events = page_data["entities"]["ZLIVE_EVENTS"]
            for x in events:
                startDate = fix_date(events[x]["startDate"])

                # if date is in the future
                if startDate > datetime.datetime.now(IST):
                    events[x]["startDate"] = startDate.isoformat()
                    events[x]["endDate"] = fix_date(events[x]["endDate"]).isoformat()

                events[x]["url"] = page_data["pages"]["current"]["canonicalUrl"]
                yield events[x]
    if not found:
        print("No events found in", url)


def fetch_data(session, url, params, cache=True):
    headers = {
        "x-city-id": "4",  # Bangalore
        "x-zomato-app-version": "17.43.5",
        "x-zomato-api-key": ZOMATO_API_KEY,
    }

    response = session.post(
        "https://api.zomato.com" + url, json=params, headers=headers, cache=cache
    )
    return response.json()


def qs(url, key="event_id"):
    q = urlparse(url).query
    if "zomaland" not in url:
        return parse_qs(q)[key][0]


def get_event_ids(session):
    jsonpath_selector = "$..['url']"
    # We don't want to cache the event list, only the events themselves
    data = fetch_data(
        session, "/gw/goout/events/search", {"theme_type": "dark"}, cache=False
    )
    return list(
        set(
            [
                qs(url)
                for url in jsonpath.findall(jsonpath_selector, data)
                if "event_id=" in url
            ]
        )
    )


if __name__ == "__main__":
    if "ZOMATO_PUBLIC_API_KEY" not in os.environ:
        raise Exception("ZOMATO_PUBLIC_API_KEY not set")
    events = []
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    session = Fetch(cache={"serializer": "json"})
    for event_id in sorted(get_event_ids(session)):
        for event in get_events(session, event_id):
            print(event["url"])
            events.append(event)
        if len(events) >= limit:
            break

    if len(events) == 0:
        import sys

        print("ZOMATO: No events found")
        sys.exit(1)

    with open("out/zomato.jsonnet", "w") as f:
        json.dump(events, f, indent=2)
