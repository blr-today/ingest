import datetime
import json
from pathlib import Path
from types import SimpleNamespace

from src.sources import timeandspace
FIXTURES = Path(__file__).parent / "fixtures/timeandspace"
API = "https://timeandspace.gallery/wp-json/tribe/events/v1/events"


class FakeSession:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        name = "events.json" if "?" in url else url.split("/")[-1] + ".json"
        return SimpleNamespace(json=lambda: json.loads((FIXTURES / name).read_text()))


class Fixed(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.datetime(2026, 10, 12, 9, 0)


def test_event_ids_start_45_days_back(monkeypatch):
    monkeypatch.setattr(timeandspace, "datetime", Fixed)
    session = FakeSession()
    assert timeandspace.fetch_event_ids(session) == [11006]
    assert session.urls == [API + "?start_date=2026-08-28"]


def test_event_cleanup():
    event = timeandspace.fetch_event(FakeSession(), 11006)
    assert event["name"] == "The Haren Thakur Show"
    assert "organizer" not in event and "performer" not in event
    assert event["description"].startswith("Haren Thakur is recognized as a modernist artist")
    assert "<p>" not in event["description"]
    assert event["location"]["address"]["streetAddress"] == "2nd Floor, The Guild, 55, Lavelle Road"


def test_events(monkeypatch):
    monkeypatch.setattr(timeandspace, "get_cached_session", FakeSession)
    [event] = timeandspace.events()
    assert event["url"] == "https://timeandspace.gallery/event/the-haren-thakur-show/"
