import json
from datetime import datetime, time
from pathlib import Path

import pytest

import mainmission
from common.tz import IST

FIXTURE = Path(__file__).parent / "fixtures" / "mainmission" / "events.json"
NOW = datetime(2026, 9, 1, tzinfo=IST)


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 1, tzinfo=tz)


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.params = []

    def get(self, url, params=None, timeout=None):
        self.params.append(params)
        return FakeResponse(self.pages[len(self.params) - 1])


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(mainmission, "datetime", Clock)


def docs():
    data = json.loads(FIXTURE.read_text())
    session = FakeSession([data])
    return {d["_id"]: d for d in mainmission.fetch_events(session)}


def test_fetch_events_follows_page_tokens():
    data = json.loads(FIXTURE.read_text())
    first = {"documents": data["documents"][:3], "nextPageToken": "abc"}
    second = {"documents": data["documents"][3:]}
    session = FakeSession([first, second])
    found = mainmission.fetch_events(session)
    assert len(found) == len(data["documents"])
    assert session.params == [{"pageSize": 300}, {"pageSize": 300, "pageToken": "abc"}]


def test_decode_value_handles_firestore_types():
    doc = docs()["9YMJklrqs0tECEIv6QYO"]
    assert doc["tags"] == ["Game", "Set", "Community"]
    assert doc["capacity"] == {"maxPlayerSlots": 102, "slotsTaken": 1}
    assert doc["soldOut"] is True
    assert mainmission.decode_value({"doubleValue": 1.5}) == 1.5
    assert mainmission.decode_value({"nullValue": None}) is None
    assert mainmission.decode_value({"timestampValue": "2026-09-30T12:36:48Z"}) is None


def test_parse_event_date_formats():
    assert str(mainmission.parse_event_date("2026-10-02")) == "2026-10-02"
    assert str(mainmission.parse_event_date("Saturday, 10 Jan 2026")) == "2026-01-10"
    assert str(mainmission.parse_event_date("Sunday, Nov 30")) == "2026-11-30"
    assert mainmission.parse_event_date("") is None
    assert mainmission.parse_event_date("soon") is None


def test_parse_time_range_formats():
    assert mainmission.parse_time_range("3-6pm") == (time(15), time(18))
    assert mainmission.parse_time_range("5PM TO 9PM ") == (time(17), time(21))
    assert mainmission.parse_time_range("06:00AM - 09:00PM") == (time(6), time(21))
    assert mainmission.parse_time_range("11:00 AM Onwards") == (time(11), None)
    assert mainmission.parse_time_range("12 AM") == (time(0), None)
    assert mainmission.parse_time_range("All Day (You will get your wave timing)") == (None, None)
    assert mainmission.parse_time_range(None) == (None, None)


def test_build_datetimes_defaults_and_overnight():
    start, end = mainmission.build_datetimes("2026-09-20", "")
    assert (start.hour, (end - start).seconds) == (9, 7200)
    start, end = mainmission.build_datetimes("2026-09-20", "10 PM - 1 AM")
    assert end.isoformat() == "2026-09-21T01:00:00+05:30"
    assert mainmission.build_datetimes(None, "7 AM") == (None, None)


def test_get_image_prefers_high_res():
    assert mainmission.get_image({"imageUrl": {"lowRes": "l", "highRes": "h"}}) == "h"
    assert mainmission.get_image({"imageUrl": "s"}) == "s"
    assert mainmission.get_image({"imageUrls": [{"lowRes": "l"}]}) == "l"
    assert mainmission.get_image({"imageUrls": ["", "u"]}) == "u"
    assert mainmission.get_image({}) is None


def test_parse_price():
    assert mainmission.parse_price("Free ") == 0.0
    assert mainmission.parse_price("RSVP PASS") == 0.0
    assert mainmission.parse_price("699 onwards") == 699.0
    assert mainmission.parse_price("1,250.50") == 1250.5
    assert mainmission.parse_price("TBA") == 0.0
    assert mainmission.parse_price(None) == 0.0


def test_is_bengaluru_rejects_other_cities():
    assert mainmission.is_bengaluru("Hyfit, HSR Layout")
    assert not mainmission.is_bengaluru("Anjuna, Goa")
    assert not mainmission.is_bengaluru("  ")


def test_visible_event_becomes_sports_event():
    event = mainmission.make_event(docs()["3yiMMroeF243t5zd5PwT"], NOW)
    assert event["name"] == "Indiranagar 5K Run"
    assert event["startDate"] == "2026-10-02T06:30:00+05:30"
    assert event["endDate"] == "2026-10-02T08:30:00+05:30"
    assert event["url"] == "https://mainmission.in/#/events/3yiMMroeF243t5zd5PwT"
    assert event["location"]["address"] == "Indiranagar, Bengaluru, Karnataka, India"
    assert event["isAccessibleForFree"] is True
    assert event["offers"][0]["price"] == "0"
    assert event["offers"][0]["availability"] == "https://schema.org/SoldOut"
    assert event["image"].startswith("https://firebasestorage.googleapis.com/")
    assert "About This Event" in event["description"]
    assert "keywords" not in event


def test_paid_event_uses_external_link_and_tags():
    doc = dict(docs()["bNVyR64iXTz9uyeAWZrp"], hidden=False, date="Saturday, 10 Oct 2026")
    event = mainmission.make_event(doc, NOW)
    assert event["offers"][0]["price"] == "699"
    assert event["offers"][0]["url"].startswith("https://app.peakst8.club/event/")
    assert event["isAccessibleForFree"] is False
    assert event["endDate"] == "2026-10-10T21:00:00+05:30"
    assert event["keywords"] == ["festival", "community", "celebration", "fitness"]


def test_bangalore_address_is_kept_verbatim():
    doc = dict(docs()["4zs8PVHTDpcjR8vcuo5W"], hidden=False, date="2026-09-13")
    event = mainmission.make_event(doc, NOW)
    assert event["location"]["address"] == event["location"]["name"]
    assert "North Bangalore" in event["location"]["address"]


def test_hidden_past_and_remote_events_are_skipped():
    found = docs()
    assert mainmission.make_event(found["0RJsm0FCQNoW3LdOX2f4"], NOW) is None
    assert mainmission.make_event(found["9YMJklrqs0tECEIv6QYO"], datetime(2026, 9, 21, tzinfo=IST)) is None
    assert mainmission.make_event(dict(found["3yiMMroeF243t5zd5PwT"], location="Goa"), NOW) is None
    assert mainmission.make_event(dict(found["3yiMMroeF243t5zd5PwT"], draft=True), NOW) is None
