from pathlib import Path
from types import SimpleNamespace

from src.sources import hsrmeetups, meetup
from src.sources.meetup import event_urls, make_event, page_event

FIXTURES = Path(__file__).parent / "fixtures/meetup"
BASE = "https://www.meetup.com/hsrmeetups/events/"


def fake_get(url, headers=None):
    name = "events.ics" if url.endswith("/ical/") else url.rstrip("/").split("/")[-1] + ".html"
    path = FIXTURES / name
    text = path.read_text() if path.exists() else "<html></html>"
    return SimpleNamespace(text=text, raise_for_status=lambda: None)


SESSION = SimpleNamespace(get=fake_get)


def test_event_urls_from_ical():
    assert event_urls(SESSION, "hsrmeetups") == [BASE + "316748925/", BASE + "316624038/", BASE + "dqbnbvyjcnbrb/"]


def test_event_with_capacity_and_venue():
    event = make_event(SESSION, BASE + "316624038/")
    assert event["name"] == "BoardGames & Dinner @HSRmeetups"
    assert event["url"] == BASE + "316624038/"
    assert event["description"].startswith("***.***\nCheck IG")
    assert event["maximumAttendeeCapacity"] == 38
    assert event["remainingAttendeeCapacity"] == 10
    assert "offers" not in event
    assert event["location"]["geo"] == {"@type": "GeoCoordinates", "latitude": 12.91814, "longitude": 77.645054}


def test_event_price_from_description():
    event = make_event(SESSION, BASE + "dqbnbvyjcnbrb/")
    assert event["offers"] == {"@type": "Offer", "price": "299", "priceCurrency": "INR"}
    assert event["remainingAttendeeCapacity"] == 33
    assert event["location"]["geo"]["latitude"] == 12.925593


def test_page_without_event(capsys):
    assert make_event(SESSION, BASE + "missing/") is None
    assert "No event found" in capsys.readouterr().err


def test_page_event_picks_matching_url():
    state = {"Event:1": {"eventUrl": "a"}, "Event:2": {"eventUrl": "b"}, "Venue:1": {}}
    assert page_event(state, "b") == {"eventUrl": "b"}
    assert page_event(state, "c") == {"eventUrl": "a"}
    assert page_event({}, "c") == {}


def test_hsrmeetups_events(monkeypatch):
    monkeypatch.setattr(meetup, "get_cached_session", lambda: SESSION)
    events = hsrmeetups.events()
    assert [e["url"] for e in events] == [BASE + "316624038/", BASE + "dqbnbvyjcnbrb/"]
