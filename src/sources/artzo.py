import json
from src.common.remote import events_from_urls
from src.common.session import get_cached_session
from bs4 import BeautifulSoup

URL = "https://www.artzo.in/events-and-workshops"
URL_PREFIX = "https://www.artzo.in/event-details/"


def fetch_events(session):
    content = session.get(URL).text
    soup = BeautifulSoup(content, "html.parser")
    data = json.loads(soup.find(id="wix-warmup-data").string)
    try:
        listed = [
            y["events"]["events"]
            for x in data["appsWarmupData"].values()
            for y in x.values()
            if "events" in y
        ][0]
        return [URL_PREFIX + event["slug"] for event in listed]
    except (KeyError, IndexError):
        return []


def urls():
    return fetch_events(get_cached_session())


def events():
    return events_from_urls(sorted(urls()))
