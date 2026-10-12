import json
from datetime import datetime
from pathlib import Path

from src.sources import tonight
from src.common import firebase
from src.sources.tonight import convert_to_event_json, fetch_parties, get_ticket_url, get_url

FIXTURE = Path(__file__).parent / "fixtures" / "tonight" / "parties.json"
KPOP = "https://insider.in/event/kpop-karaoke-party-from-seoul-to-tokyo-may31-2024/buy-page"


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return FakeResponse(self.pages[url])


def documents():
    return json.loads(FIXTURE.read_text())["documents"]


def parties():
    return firebase.Firebase.parse_firebase_struct(documents())


def paged(monkeypatch):
    docs = documents()
    session = FakeSession({
        tonight.URL: {"documents": docs[:2], "nextPageToken": "abc"},
        f"{tonight.URL}&pageToken=abc": {"documents": docs[2:]},
    })
    monkeypatch.setattr(tonight, "get_cached_session", lambda: session)
    return session


def test_urls_prefer_party_page_then_fallbacks():
    assert get_url({"id": "abc", "ticketUrl": KPOP}) == "https://www.tonight.is/party/abc"
    assert get_url({"ticketUrl": KPOP}) == KPOP
    assert get_ticket_url({"id": "TPMygSSqmlO6qnhm7gaG", "ticketUrl": KPOP}).startswith("https://www.district.in/events/echoes-of-earth")
    assert get_ticket_url({"id": "abc", "ticketUrl": KPOP}) == KPOP


def test_converts_party():
    event = convert_to_event_json(parties()[0])
    assert event["@type"] == "MusicEvent"
    assert event["name"] == "K-pop Karaoke Party - From Seoul to Tokyo"
    assert event["about"].startswith("Join us at 2 Moons for a K-Pop Karaoke Party")
    assert event["url"] == KPOP
    assert event["sameAs"] == KPOP
    assert event["offers"] == {"@type": "Offer", "url": KPOP}
    assert event["startDate"] == "2024-05-31T19:00:00+05:30"
    assert event["endDate"] == "2024-05-31T23:30:00+05:30"
    assert "1qEL9ZTAu831FptwLpgi" in event["image"]
    assert event["performer"] == {"@type": "MusicGroup", "name": "Various Artists"}
    assert event["organizer"]["name"] == "Redtable Communications Private Limited"
    assert event["location"]["name"] == "2 Moons"
    assert event["location"]["address"]["addressLocality"] == "Bangalore"
    assert event["location"]["address"]["streetAddress"].startswith("5th floor, 1, MG Mall")


def test_party_without_banner():
    party = dict(parties()[1], bannerImages=[])
    assert convert_to_event_json(party)["image"] is None


def test_fetch_parties_follows_page_token(monkeypatch):
    session = paged(monkeypatch)
    assert len(list(fetch_parties())) == 3
    assert session.urls == [tonight.URL, f"{tonight.URL}&pageToken=abc"]


def test_events_are_upcoming_parties(monkeypatch):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 6, 1)

    paged(monkeypatch)
    monkeypatch.setattr(tonight, "datetime", FrozenDatetime)
    events = tonight.events()
    assert [e["name"] for e in events] == ["Boiler Room Bangalore", "Sunburn Arena Ft. Alan Walker - Bengaluru"]


def test_known_venues_get_coordinates():
    kpop, _, sunburn = parties()
    assert convert_to_event_json(kpop)["location"]["geo"] == {
        "@type": "GeoCoordinates",
        "latitude": "12.9734662",
        "longitude": "77.6204084",
    }
    assert "geo" not in convert_to_event_json(sunburn)["location"]
