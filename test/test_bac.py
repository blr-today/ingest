import json
from datetime import datetime
from pathlib import Path

from src.sources import bac
from src.sources.bac import fetch_events, fetch_min_price, guess_event_type, is_outside_blr, make_event, make_location, parse_ist, strip_html
from src.common.tz import IST

FIXTURES = Path(__file__).parent / "fixtures" / "bac"
ORIONIDS = "https://bangaloreastronomyclub.com/event/orionids-meteor-shower-meteors-midnight-magic/"
EXHIBITION = "https://bangaloreastronomyclub.com/event/astro-photography-exhibition-4-0/"
NOW = datetime(2026, 10, 1, tzinfo=IST)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def json(self):
        return json.loads(self.text)


class FakeSession:
    def __init__(self, pages=None):
        self.pages = pages if pages is not None else {
            ORIONIDS: (FIXTURES / "orionids.html").read_text(),
            EXHIBITION: (FIXTURES / "exhibition.html").read_text(),
        }
        self.listing = (FIXTURES / "events.json").read_text()
        self.params = []

    def get(self, url, params=None, timeout=None):
        if url == bac.EVENTS_API:
            self.params.append(params)
            return FakeResponse(self.listing)
        if url not in self.pages:
            raise ConnectionError(url)
        return FakeResponse(self.pages[url])


def raw_events():
    return json.loads((FIXTURES / "events.json").read_text())["events"]


def test_helpers():
    assert strip_html("Orionids Meteor Shower &#8211; Meteors &#038; Midnight Magic") == "Orionids Meteor Shower – Meteors & Midnight Magic"
    assert strip_html(None) == ""
    assert parse_ist("2026-10-20 16:00:00").isoformat() == "2026-10-20T16:00:00+05:30"
    assert guess_event_type([{"name": "Stargazing Night"}]) == "EducationEvent"
    assert guess_event_type(None) == "EducationEvent"


def test_outside_city_venues():
    orionids, exhibition = raw_events()
    assert is_outside_blr(orionids["venue"])
    assert not is_outside_blr(exhibition["venue"])
    assert is_outside_blr({"venue": "Satya Anantham", "city": "Chikkaballapura"})


def test_location_from_venue():
    assert make_location(raw_events()[1]["venue"]) == {
        "@type": "Place",
        "name": "Venkatappa Art Gallery",
        "address": {
            "@type": "PostalAddress",
            "addressCountry": "India",
            "streetAddress": "Kasturba Rd, Ambedkar Veedhi, Sampangi Rama Nagar",
            "addressLocality": "BANGALORE",
            "addressRegion": "Karnataka",
            "postalCode": "560001",
        },
    }
    assert make_location({})["name"] == "Bangalore Astronomy Club"


def test_cheapest_package_price():
    session = FakeSession()
    assert fetch_min_price(session, ORIONIDS) == 4700
    assert fetch_min_price(session, EXHIBITION) == 0
    assert fetch_min_price(FakeSession({ORIONIDS: "<html></html>"}), ORIONIDS) is None
    assert fetch_min_price(FakeSession({}), ORIONIDS) is None


def test_paid_camp_outside_city():
    event = make_event(FakeSession(), raw_events()[0], NOW)
    assert event["@type"] == "EducationEvent"
    assert event["name"] == "Orionids Meteor Shower – Meteors & Midnight Magic"
    assert event["description"].startswith("Join the stargazing camping near Bangalore")
    assert event["startDate"] == "2026-10-20T16:00:00+05:30"
    assert event["endDate"] == "2026-10-21T09:30:00+05:30"
    assert event["image"].endswith("/IMG_20181203_223007.jpg")
    assert event["offers"][0]["price"] == "4700"
    assert event["keywords"] == ["NOTINBLR"]
    assert "isAccessibleForFree" not in event


def test_free_exhibition_in_city():
    event = make_event(FakeSession(), raw_events()[1], NOW)
    assert event["@type"] == "ExhibitionEvent"
    assert event["isAccessibleForFree"] is True
    assert "offers" not in event
    assert "keywords" not in event


def test_unpriced_event_without_image():
    raw = dict(raw_events()[1], image=False)
    event = make_event(FakeSession({}), raw, NOW)
    assert "image" not in event
    assert "offers" not in event
    assert "isAccessibleForFree" not in event


def test_past_events_are_skipped():
    assert make_event(FakeSession(), raw_events()[0], datetime(2026, 10, 21, tzinfo=IST)) is None


def test_fetch_events_pages_through():
    session = FakeSession()
    listing = json.loads(session.listing)
    session.listing = json.dumps(dict(listing, total_pages=2))
    assert len(fetch_events(session)) == 4
    assert [p["page"] for p in session.params] == [1, 2]


def test_events_are_upcoming(monkeypatch):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 1, tzinfo=IST)

    monkeypatch.setattr(bac, "datetime", FrozenDatetime)
    monkeypatch.setattr(bac, "get_cached_session", FakeSession)
    [event] = bac.events()
    assert event["url"] == EXHIBITION
