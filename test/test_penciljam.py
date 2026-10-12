from pathlib import Path

from src.sources import penciljam
from src.sources.penciljam import fetch_event_urls, fetch_ical, parse_ical_event

FIXTURES = Path(__file__).parent / "fixtures" / "penciljam"
URL = "https://penciljam.com/main/events/penciljam-at-military-memorial-igmf/"
CUBBON = "https://penciljam.com/main/events/penciljam-bengaluru-at-cubbon-park-tree-3335-2/"


class FakeResponse:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        if url not in self.pages:
            return FakeResponse(404)
        return FakeResponse(200, self.pages[url])


def ical():
    return (FIXTURES / "military-memorial.ics").read_bytes().decode()


def test_parses_ical_event():
    event = parse_ical_event(ical(), URL)
    assert event["name"] == "Penciljam at Military memorial (IGMF)"
    assert event["url"] == URL
    assert event["startDate"] == "2026-10-11T10:00:00+05:30"
    assert event["endDate"] == "2026-10-11T12:00:00+05:30"
    assert "📆 11th Oct 2026" in event["description"]
    assert event["location"] == {
        "@type": "Place",
        "name": "Military memorial (IGMF)",
        "url": "https://maps.app.goo.gl/VUEeDR66aMZdxg4m9",
    }


def test_instant_event_lasts_two_hours():
    text = ical().replace("DTEND;TZID=Asia/Kolkata:20261011T120000", "DTEND;TZID=Asia/Kolkata:20261011T100000")
    assert parse_ical_event(text, URL)["endDate"] == "2026-10-11T12:00:00+05:30"


def test_location_text_is_kept():
    text = ical().replace("SUMMARY:Penciljam at Military memorial (IGMF)", "SUMMARY:Penciljam Sunday Jam")
    text = text.replace("LOCATION:https://maps.app.goo.gl/VUEeDR66aMZdxg4m9", "LOCATION:Cubbon Park")
    assert parse_ical_event(text, URL)["location"] == {"@type": "Place", "name": "Cubbon Park"}
    text = text.replace("LOCATION:Cubbon Park\r\n", "").replace("LOCATION:Cubbon Park\n", "")
    assert "location" not in parse_ical_event(text, URL)


def test_unnamed_or_broken_ical_is_skipped():
    assert parse_ical_event(ical().replace("SUMMARY:Penciljam at Military memorial (IGMF)", "SUMMARY:"), URL) is None
    assert parse_ical_event("<html>Not found</html>", URL) is None


def test_listing_urls(monkeypatch):
    monkeypatch.setattr(penciljam, "session", FakeSession({penciljam.EVENTS_URL: (FIXTURES / "events.html").read_text()}))
    assert fetch_event_urls() == [URL, CUBBON]


def test_empty_or_failed_listing(monkeypatch):
    monkeypatch.setattr(penciljam, "session", FakeSession({penciljam.EVENTS_URL: (FIXTURES / "empty.html").read_text()}))
    assert fetch_event_urls() == []
    monkeypatch.setattr(penciljam, "session", FakeSession({}))
    assert fetch_event_urls() == []


def test_fetch_ical(monkeypatch):
    monkeypatch.setattr(penciljam, "session", FakeSession({URL + "ical/": ical()}))
    assert fetch_ical(URL).startswith("BEGIN:VCALENDAR")
    assert fetch_ical(CUBBON) is None


def test_events(monkeypatch):
    monkeypatch.setattr(penciljam, "session", FakeSession({
        penciljam.EVENTS_URL: (FIXTURES / "events.html").read_text(),
        URL + "ical/": ical(),
    }))
    [event] = penciljam.events()
    assert event["url"] == URL
