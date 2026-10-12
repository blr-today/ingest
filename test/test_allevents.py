import json
import time
from pathlib import Path

import pytest

from src.processors.allevents import AllEvents

ROWS = json.loads(
    (Path(__file__).parent / "fixtures/processors/events.json").read_text()
)


def listing():
    url, event = next(r for r in ROWS if "allevents" in r[0])
    return url, json.loads(json.dumps(event))


@pytest.fixture(params=["UTC", "Asia/Tokyo"])
def utc(monkeypatch, request):
    monkeypatch.setenv("TZ", request.param)
    time.tzset()
    yield
    monkeypatch.undo()
    time.tzset()


def test_clean_listing_is_untouched():
    url, event = listing()
    assert AllEvents.process(url, json.loads(json.dumps(event))) == event


def test_broken_offsets_become_ist(utc):
    url, event = listing()
    event["startDate"] = "2026-03-06T11:30:00+.000+0"
    event = AllEvents.process(url, event)
    assert event["startDate"] == "2026-03-06T17:00:00+05:30"
    assert event["endDate"] == "2026-03-06T19:00:00+05:30"


def test_placeholder_geo_is_dropped():
    url, event = listing()
    event["location"]["geo"] = {"latitude": "12.9716", "longitude": "77.5946"}
    assert "geo" not in AllEvents.process(url, event)["location"]
    event["location"]["geo"] = {"latitude": 12.97165, "longitude": 77.59455}
    assert "geo" not in AllEvents.process(url, event)["location"]


def test_odd_geo_is_kept():
    url, event = listing()
    for geo in (
        {"latitude": "?", "longitude": "77.5946"},
        {"latitude": "12.9716"},
        None,
    ):
        event["location"]["geo"] = geo
        assert AllEvents.process(url, event)["location"]["geo"] == geo
    event["location"] = "Bangalore"
    assert AllEvents.process(url, event)["location"] == "Bangalore"


def test_missing_or_unreadable_dates_are_kept(caplog):
    url, event = listing()
    del event["endDate"]
    event["startDate"] = None
    assert AllEvents.process(url, json.loads(json.dumps(event))) == event
    event["startDate"] = "TBA+.000+0"
    assert AllEvents.process(url, json.loads(json.dumps(event))) == event
    assert f"AllEvents could not read startDate 'TBA+.000+0' for {url}" in caplog.text
