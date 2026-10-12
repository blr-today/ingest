import datetime
import json
from pathlib import Path
from types import SimpleNamespace

from src.sources import gullytours
FIXTURES = Path(__file__).parent / "fixtures/gullytours"
CRAWL = {"url": "https://www.gully.tours/tours/colonial-crawl", "id": "36715", "name": "Colonial Crawl"}
PETE = {"url": "https://www.gully.tours/tours/pete-by-night", "id": "9094", "name": "Pete by Night"}


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url, params))
        if url.endswith("departure_calendar.json"):
            path = FIXTURES / f"calendar-{url.split('/')[-2]}.json"
            return SimpleNamespace(json=lambda: json.loads(path.read_text()))
        return SimpleNamespace(content=(FIXTURES / "pete-by-night.html").read_bytes())


class Fixed(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.datetime(2026, 10, 12, 9, 0)


def test_description_skips_filler():
    desc = gullytours.get_description(FakeSession(), PETE["url"])
    assert desc.startswith("Explore the evening vibe of the oldest neighbourhood")
    assert "Lorem" not in desc and "Dolor" not in desc


def test_calendar_departures(monkeypatch):
    monkeypatch.setattr(gullytours, "datetime", Fixed)
    session = FakeSession()
    [trip] = gullytours.get_calendar(session, "36715")
    assert trip == {
        "starts_at": "2026-10-17T07:30:00",
        "ends_at": "2026-10-17T10:30:00",
        "min_pax": 1,
        "available_seats": 12,
        "total_capacity": 12,
        "price": "1500",
    }
    [(url, params)] = session.calls
    assert url == "https://gullytours.vacationlabs.com/itineraries/trips/36715/departure_calendar.json"
    assert params == {"start": "2026-10-12", "end": "2026-11-11"}


def test_calendar_without_departures():
    assert list(gullytours.get_calendar(FakeSession(), "9094")) == []
    assert list(gullytours.get_calendar(SimpleNamespace(get=lambda url, params: SimpleNamespace(json=dict)), "1")) == []


def test_make_event():
    [trip] = gullytours.get_calendar(FakeSession(), "36715")
    event = gullytours.make_event(CRAWL, "A walk", trip)
    assert event["name"] == "Colonial Crawl"
    assert event["startDate"] == "2026-10-17T07:30:00+05:30"
    assert event["endDate"] == "2026-10-17T10:30:00+05:30"
    assert event["maximumAttendeeCapacity"] == 12
    assert event["remainingAttendeeCapacity"] == 12
    assert event["offers"] == [{"@type": "Offer", "price": "1500", "priceCurrency": "INR"}]


def test_read_config():
    assert CRAWL in gullytours.read_config()


def test_events(monkeypatch):
    monkeypatch.setattr(gullytours, "get_cached_session", FakeSession)
    monkeypatch.setattr(gullytours, "read_config", lambda: [CRAWL, PETE])
    [event] = gullytours.events()
    assert event["url"] == CRAWL["url"]
