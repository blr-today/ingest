from bs4 import BeautifulSoup
from src.common.session import get_cached_session
import html
from datetime import datetime, timedelta


def fetch_event(session, id: str):
    # Fetch event description from detail page
    event_json = session.get(
        f"https://timeandspace.gallery/wp-json/tribe/events/v1/events/{id}"
    ).json()["json_ld"]
    # These two fields are incorrectly filled
    if "organizer" in event_json:
        del event_json["organizer"]
    if "performer" in event_json:
        del event_json["performer"]
    event_json["description"] = BeautifulSoup(
        html.unescape(event_json["description"]), "html.parser"
    ).text
    return event_json


def fetch_event_ids(session):
    starting_date = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
    url = f"https://timeandspace.gallery/wp-json/tribe/events/v1/events?start_date={starting_date}"
    events = session.get(url).json()["events"]
    return [event["id"] for event in events]


def events():
    session = get_cached_session()
    return [fetch_event(session, id) for id in fetch_event_ids(session)]
