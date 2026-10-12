import json
from datetime import datetime
from pathlib import Path

import pytest

from src.processors import koota
from src.processors.koota import Koota, fetch_record

FIXTURES = Path(__file__).parent / "fixtures/koota"
EVENTS = json.loads((FIXTURES / "events.json").read_text())
RECORDS = json.loads((FIXTURES / "record.json").read_text())


class FakeSession:
    def __init__(self, records):
        self.records, self.calls = records, []

    def get(self, url, params, timeout):
        self.calls.append(params["slug"])
        if isinstance(self.records, Exception):
            raise self.records
        records = self.records
        return type(
            "Response",
            (),
            {"raise_for_status": lambda s: None, "json": lambda s: records},
        )()


@pytest.fixture
def api(monkeypatch):
    session = FakeSession([])
    monkeypatch.setattr(koota, "get_cached_session", lambda: session)
    return session


def test_scraped_dates_become_iso(api):
    for event in EVENTS:
        event = Koota.process(event["url"], dict(event))
        for key in ("startDate", "endDate"):
            assert datetime.fromisoformat(event[key]).utcoffset().seconds == 19800
    assert EVENTS[0]["startDate"] == "2026-10-25T12:00+5.5:00"
    assert Koota.process("u", dict(EVENTS[0]))["startDate"] == "2026-10-25T12:00+05:30"


def test_single_digit_parts_are_padded(api):
    event = {"startDate": "2026-1-5T19:00+5.5:00", "endDate": "2026-12-5"}
    assert Koota.process("u", event) == {
        "startDate": "2026-01-05T19:00+05:30",
        "endDate": "2026-12-05",
    }


def test_odd_dates_are_left_alone(api):
    event = {"startDate": "Oct 5, 2026", "name": "x"}
    assert Koota.process("u", event) == {"startDate": "Oct 5, 2026", "name": "x"}


def test_rest_record_sets_type_and_description(api):
    api.records = RECORDS
    event = Koota.process(EVENTS[0]["url"], dict(EVENTS[0], keywords=["KOOTA"]))
    assert api.calls == ["bengaluru-boy-by-danish-sait-stand-up-comedy"]
    assert event["@type"] == "ComedyEvent"
    assert event["keywords"] == ["KOOTA"]
    assert event["description"].startswith(
        "The Bengaluru Boy is coming to Courtyard Koota!\n"
    )
    assert "<" not in event["description"]


def test_failed_lookup_is_skipped(api, caplog):
    assert fetch_record("https://courtyardkoota.com/events/x/") is None
    api.records = OSError("offline")
    event = Koota.process(EVENTS[1]["url"], dict(EVENTS[1]))
    assert event["@type"] == "Event" and "description" not in event
    assert "Koota REST lookup failed" in caplog.text


def test_unreadable_dates_are_left_alone(api):
    event = {"startDate": "Tue, 5 Oct 2026", "endDate": None, "name": "x"}
    assert Koota.process("u", dict(event)) == event


def test_unexpected_response_is_skipped(api, caplog):
    api.records = {"code": "rest_no_route"}
    assert fetch_record("https://courtyardkoota.com/events/x/") is None
    assert "Koota REST lookup failed" in caplog.text
