import jsonpath
from urllib.parse import urlparse, parse_qs
import os
from common.session import get_cached_session
from common import USER_AGENT_HEADERS

# Public Key, not-logged-in API key
ZOMATO_API_KEY = os.environ.get("ZOMATO_PUBLIC_API_KEY")
BASE_URL = "https://zoma.to/live-event/"


def fetch_data(url, body):
    session = get_cached_session()
    headers = {
        "x-city-id": "4",  # Bangalore
        "x-zomato-app-version": "17.43.5",
        "x-zomato-api-key": ZOMATO_API_KEY,
        "accept": "*/*"
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
    for event_id in get_event_ids():
        if event_id:
            print(BASE_URL + event_id)