import jsonpath
import re
import json
from urllib.parse import urlparse, parse_qs
from curl_cffi import requests as curl_impersonate
import datetime
from common.tz import IST
import os
from common.session import get_cached_session
from common import USER_AGENT_HEADERS


# Public Key, not-logged-in API key
ZOMATO_API_KEY = os.environ.get("ZOMATO_PUBLIC_API_KEY")
BASE_URL = "https://zoma.to/live-event/"
KNOWN_BAD_EVENTS = ["43612"]  # SkyJumper Trampoline Park, too long


def fix_date(date_str):
    return datetime.datetime.fromisoformat(date_str).replace(tzinfo=IST)


def get_events(event_id):
    if event_id in KNOWN_BAD_EVENTS:
        return
    url = f"{BASE_URL}{event_id}"
    r = curl_impersonate.get(url, impersonate="chrome")
    if "window.location.replace" in r.text:
        redirect = r.text.split('window.location.replace("')[1].split('")')[0]
        r = curl_impersonate.get(redirect, impersonate="chrome")
    # find all script tags using beautifulsoup
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(r.text, "html.parser")
    scripts = soup.find_all("script")
    for script in scripts:
        if "__PRELOADED_STATE__" in script.text:
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


def fetch_data(url, body):
    session = get_cached_session()
    headers = {
        "x-city-id": "4",  # Bangalore
        "x-zomato-app-version": "17.43.5",
        "x-zomato-api-key": ZOMATO_API_KEY,
        "accept": "*/*",
    } | USER_AGENT_HEADERS

    response = session.post("https://api.zomato.com" + url, json=body, headers=headers)
    return response.json()


def qs(url, key="event_id"):
    q = urlparse(url).query
    if "zomaland" not in url:
        return parse_qs(q)[key][0]


def get_event_ids():
    jsonpath_selector = "$..['url']"
    data = fetch_data("/gw/goout/events/search", {"theme_type": "dark"})
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
    for event_id in get_event_ids():
        for event in get_events(event_id):
            events.append(event)

    with open("out/zomato.jsonnet", "w") as f:
        json.dump(events, f, indent=2)
