import datetime
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import champaca

FIXTURES = Path(__file__).parent / "fixtures" / "champaca"
MOVING_LINE = "https://champaca.in/products/book-launch-a-moving-line-evolving-identities-in-comics-and-graphic-narratives"
MEDU_VADA = "https://champaca.in/products/brunch-books-for-kids-read-aloud-of-manvinder-s-medu-vada"


class Clock(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 1, 9, 0)


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def json(self):
        return json.loads(self.text)


def fake_request(url):
    if url == "https://champaca.in/blogs/events.atom":
        return FakeResponse((FIXTURES / "events.atom").read_text())
    path = FIXTURES / url.rsplit("/", 1)[-1]
    if not path.suffix:
        path = path.with_suffix(".html")
    return FakeResponse(path.read_text() if path.exists() else "")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(champaca, "make_request", fake_request)
    monkeypatch.setattr(champaca, "datetime", SimpleNamespace(datetime=Clock, timedelta=datetime.timedelta))


def published():
    return datetime.datetime(2026, 9, 29, 16, 39)


def test_schedule_with_time_range():
    text = "Date: 10th October 2026, Saturday Time: 11:00 AM to 12:30 PM Venue: Champaca Bookstore"
    start, end = champaca.parse_schedule(text, published())
    assert start == datetime.datetime(2026, 10, 10, 11, 0)
    assert end == datetime.datetime(2026, 10, 10, 12, 30)


def test_schedule_takes_first_day_of_range_and_rolls_year():
    text = "Date:\xa026th and 27th September (Sat & Sun) Time: 11 am - 2 pm (both days)"
    start, end = champaca.parse_schedule(text, datetime.datetime(2026, 10, 5))
    assert start == datetime.datetime(2027, 9, 26, 11, 0)
    assert end == datetime.datetime(2027, 9, 26, 14, 0)


def test_schedule_without_date_or_with_bad_date():
    assert champaca.parse_schedule("Join our book club", published()) == (None, None)
    assert champaca.parse_schedule("Date: 31st February Time: 4 pm", published()) == (None, None)


def test_event_type_from_title():
    assert champaca.guess_event_type("Workshop | Cityscapes") == "EducationEvent"
    assert champaca.guess_event_type("Book Launch | Spectacle State") == "LiteraryEvent"
    assert champaca.guess_event_type("Children's Storytelling") == "ChildrensEvent"
    assert champaca.guess_event_type("Wild in the Capital") == "Event"


def test_make_event_strips_date_parts_and_defaults_end():
    start = datetime.datetime(2026, 6, 27, 11, 0)
    event = champaca.make_event("Wild in the Capital: Finding Nature | 27 June", start, None, "d", "u", [])
    assert event["name"] == "Wild in the Capital: Finding Nature"
    assert event["startDate"] == "2026-06-27T11:00:00+05:30"
    assert event["endDate"] == "2026-06-27T13:00:00+05:30"
    assert event["offers"] == []


def test_non_ticket_products_are_not_offers(monkeypatch, capsys):
    monkeypatch.setattr(champaca, "get_product_details", lambda handle: ("499", "Books"))
    start = datetime.datetime(2026, 10, 10, 18, 0)
    event = champaca.make_event("Book Launch", start, None, "d", "u", [MEDU_VADA, "https://champaca.in/products/gone"])
    assert event["offers"] == []
    assert "Could not get handle" in capsys.readouterr().out


def test_product_handle_from_canonical_link():
    assert champaca.get_product_handle(MOVING_LINE) == MOVING_LINE.rsplit("/", 1)[-1]


def test_product_details_rounds_price():
    assert champaca.get_product_details(MEDU_VADA.rsplit("/", 1)[-1]) == ("1499", "Event Tickets")


def test_fetch_events_from_feed(capsys):
    events = {e["url"].rsplit("/", 1)[-1]: e for e in champaca.fetch_events()}
    assert set(events) == {
        "book-launch-a-moving-line-evolving-identities-in-comics-and-graphic-narratives",
        "brunch-books-for-kids-read-aloud-of-manvinder-s-medu-vada",
    }
    assert "Could not find date for Lost & Found" in capsys.readouterr().out
    brunch = events["brunch-books-for-kids-read-aloud-of-manvinder-s-medu-vada"]
    assert brunch["@type"] == "LiteraryEvent"
    assert brunch["startDate"] == "2026-10-10T11:00:00+05:30"
    assert brunch["endDate"] == "2026-10-10T12:30:00+05:30"
    assert "Manvinder" in brunch["description"]
    assert {(o["url"], o["price"]) for o in brunch["offers"]} == {(MEDU_VADA, "1499")}
    assert "isAccessibleForFree" not in brunch


def test_free_event_is_marked_free():
    [event] = [e for e in champaca.fetch_events() if "Moving Line" in e["name"]]
    assert event["startDate"] == "2026-10-31T18:00:00+05:30"
    assert event["isAccessibleForFree"] is True
    assert {o["price"] for o in event["offers"]} == {"0"}


def test_fetch_events_with_broken_feed(monkeypatch):
    monkeypatch.setattr(champaca, "make_request", lambda url: FakeResponse("<feed"))
    assert champaca.fetch_events() == []
