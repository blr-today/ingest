from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from src.sources import blrbirders

FIXTURES = Path(__file__).parent / "fixtures/blrbirders"


class FakeFetch:
    def __init__(self, browser=None):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        name = "home" if url == blrbirders.URL else url.rstrip("/").split("/")[-1]
        return SimpleNamespace(text=(FIXTURES / f"{name}.html").read_text())


@pytest.fixture
def events(monkeypatch):
    monkeypatch.setattr(blrbirders, "fetcher", FakeFetch())
    soup = BeautifulSoup((FIXTURES / "home.html").read_text(), "html.parser")
    return {e["name"]: e for e in blrbirders.parse_bng_bird_events(soup)}


def test_location_with_coordinates(monkeypatch):
    monkeypatch.setattr(blrbirders, "fetcher", FakeFetch())
    url = "https://blrbirders.com/events/first-sunday-bird-walk"
    assert blrbirders.fetch_event_location(url) == ("Saul Kere [Savala Kere] East Entrance", "12.919584", "77.682765")


def test_location_without_coordinates(monkeypatch):
    monkeypatch.setattr(blrbirders, "fetcher", FakeFetch())
    name, lat, lng = blrbirders.fetch_event_location("https://blrbirders.com/events/second-sunday-walk-bmkaval")
    assert name and lat is None and lng is None


def test_parses_all_jsonld_events(events):
    assert list(events) == ["First Sunday Bird Walk", "Second Sunday Walk", "Fourth Sunday Bird Walk"]


def test_event_fields(events):
    event = events["First Sunday Bird Walk"]
    assert event["@id"] == "com.blrbirders:event_666_16"
    assert event["url"] == "https://blrbirders.com/events/first-sunday-bird-walk"
    assert event["startDate"] == "2026-02-01T07:00:00+05:30"
    assert event["endDate"] == "2026-02-01T09:30:00+05:30"
    assert event["description"].startswith("First Sunday Outing")
    assert "<" not in event["description"]
    assert "organizer" not in event
    assert event["location"]["geo"] == {"@type": "GeoCoordinates", "latitude": "12.919584", "longitude": "77.682765"}


def test_truncated_jsonld_is_repaired(events):
    event = events["Fourth Sunday Bird Walk"]
    assert event["startDate"] == "2026-02-22T07:00:00+05:30"
    assert "\nMeeting time: 7 am" in event["description"]
    assert event["location"]["name"] == "Valley School, KFI, Bangalore"
    assert "geo" not in events["Second Sunday Walk"]["location"]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_events(monkeypatch):
    monkeypatch.setattr(blrbirders, "fetcher", FakeFetch())
    assert len(blrbirders.events()) == 3


def test_unparseable_jsonld_is_skipped(monkeypatch, capsys):
    monkeypatch.setattr(blrbirders, "fetcher", FakeFetch())
    soup = BeautifulSoup((FIXTURES / "home.html").read_text(), "html.parser")
    broken = soup.new_tag("script", type="application/ld+json")
    broken.string = '{"@context": "http://schema.org",\n"@id": "event_broken"'
    soup.find("script").insert_after(broken)
    events = blrbirders.parse_bng_bird_events(soup)
    assert [e["@id"] for e in events] == ["com.blrbirders:event_666_16", "com.blrbirders:event_739_1", "com.blrbirders:event_664_17"]
    assert '"@id": "event_broken"' in capsys.readouterr().out
