import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.sources import adidas
BODY = (Path(__file__).parent / "fixtures/adidas/events.json").read_bytes()


@pytest.fixture
def requests(monkeypatch):
    calls = []

    def get(url, impersonate):
        calls.append((url, impersonate))
        return SimpleNamespace(content=BODY)

    monkeypatch.setattr(adidas.curl_cffi, "get", get)
    return calls


def test_date_in_ist():
    assert adidas._date("2026-10-22T00:30:00.000Z") == "2026-10-22T06:00:00+05:30"


def test_description_adds_distance():
    assert adidas._description({"description": " Run \n", "meta": {"distanceInM": 10000}}) == "Run\nDistance: 10 km"
    assert adidas._description({"description": "Run", "meta": {"distanceInM": 2500}}) == "Run\nDistance: 2.5 km"
    assert adidas._description({"description": "Dance", "meta": {}}) == "Dance"


def test_fetch_events(requests):
    speed, fartlek, dance = adidas.fetch_events()
    [(url, browser)] = requests
    assert url.endswith("/events/communities/2e012594-d3fb-4185-b12b-78dead3499a3?countryCodes=IN")
    assert browser == "safari184_ios"
    assert speed["name"] == "Adidas Runners Speed Session"
    assert speed["description"] == "Speed Session\nLed by Anil, Sebani\nDistance: 5 km"
    assert speed["url"] == "https://www.adidas.co.in/adidasrunners/events/event/378534619"
    assert speed["startDate"] == "2026-10-22T06:00:00+05:30"
    assert speed["endDate"] == "2026-10-22T08:00:00+05:30"
    assert speed["image"].startswith("https://res.cloudinary.com/adidas-app/")
    assert speed["location"] == {"@type": "Place", "name": "adidas Store Indiranagar", "address": "adidas Store Indiranagar Bengaluru"}
    assert fartlek["description"].endswith("Distance: 10 km")
    assert dance["description"] == "Dance fitness @ Cult Indiranagar"


def test_main_writes_events(requests, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    adidas.main()
    assert len(json.loads((tmp_path / "out/adidas.json").read_text())) == 3
