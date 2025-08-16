import json
from src.common.session import get_cached_session
from bs4 import BeautifulSoup

URL = "https://www.artzo.in/events-and-workshops"
URL_PREFIX = "https://www.artzo.in/event-details/"


def fetch_events(session):
    content = session.get(URL).text
    soup = BeautifulSoup(content, "html.parser")
    data = json.loads(soup.find(id="wix-warmup-data").string)
    try:
        for event in [
            y["events"]["events"]
            for x in data["appsWarmupData"].values()
            for y in x.values()
            if "events" in y
        ][0]:
            print(URL_PREFIX + event["slug"])
    except (KeyError, IndexError):
        pass


if __name__ == "__main__":
    session = get_cached_session()
    fetch_events(session)
