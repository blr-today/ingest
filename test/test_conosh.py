import datetime
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import conosh

FIXTURES = Path(__file__).parent / "fixtures" / "conosh"
LISTING = "https://conosh.com/pop-up/an-evening-with-cenci-italy-meets-kyoto-bengaluru-culinary-experience-aug-7-2026-"


class FakeResponse:
    def __init__(self, content, status_code=200):
        self.content = content
        self.status_code = status_code


class FakeSession:
    pages = {}

    def get(self, url):
        if url == "https://conosh.com/physical-events":
            return FakeResponse((FIXTURES / "physical-events.html").read_bytes())
        if url in self.pages:
            return FakeResponse(self.pages[url])
        return FakeResponse(b"", 404)


def clock(*args):
    class Clock(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(*args, tzinfo=tz)

    return SimpleNamespace(datetime=Clock)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    FakeSession.pages = {LISTING: (FIXTURES / "event.html").read_bytes()}
    monkeypatch.setattr(conosh, "get_cached_session", FakeSession)


def test_event_links_from_listing():
    assert conosh.get_event_links() == {LISTING}


def test_event_page_splits_dates():
    first, second = conosh.parse_event_page(LISTING)
    assert first["name"] == "Flavours from Norway by Chef Andrea Selvaggini from Savage, Oslo"
    assert first["url"] == LISTING
    assert first["startDate"][5:] == "08-08T19:30:00+05:30"
    assert second["startDate"][5:] == "08-09T19:30:00+05:30"
    assert first["image"] == "https://conosh.com/uploads/event/6ba7b1dcf2af86b01f9cab230c14145f.jpg"
    assert first["location"] == {"@type": "Place", "name": "Alba", "address": "Alba, JW Marriott Hotel Bengaluru"}


def test_offers_are_grouped_by_date():
    first, second = conosh.parse_event_page(LISTING)
    assert [o["price"] for o in first["offers"]] == ["10170", "11864", "10170", "11864"]
    assert all(o["name"].startswith("Aug 8th |") for o in first["offers"])
    assert all(o["name"].startswith("Aug 9th |") for o in second["offers"])
    assert first["offers"][0]["priceCurrency"] == "INR"


def test_missing_page_returns_none():
    assert conosh.parse_event_page("https://conosh.com/pop-up/gone") is None


def test_page_without_title_has_no_events():
    FakeSession.pages["https://conosh.com/pop-up/blank"] = b"<html><body><p>Coming soon</p></body></html>"
    assert conosh.parse_event_page("https://conosh.com/pop-up/blank") == []


def test_events_outside_bangalore_are_skipped():
    page = (FIXTURES / "event.html").read_bytes().replace(b"JW Marriott Hotel Bengaluru", b"Taj Mahal Palace Mumbai")
    FakeSession.pages[LISTING] = page
    assert conosh.parse_event_page(LISTING) == []


def test_main_keeps_future_events(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    monkeypatch.setattr(conosh, "datetime", clock(2025, 8, 1))
    conosh.main()
    assert len(json.loads((tmp_path / "out" / "conosh.json").read_text())) == 2


def test_main_drops_past_events(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    monkeypatch.setattr(conosh, "datetime", clock(2026, 12, 1))
    conosh.main()
    assert json.loads((tmp_path / "out" / "conosh.json").read_text()) == []
