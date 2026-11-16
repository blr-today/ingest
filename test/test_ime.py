import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.common import icalendar
from src.sources import ime

FIXTURES = Path(__file__).parent / "fixtures" / "ime"
PARVATHY = "https://indianmusicexperience.org/mec-events/musicians-in-the-museum-parvathy-baul/"


def freeze(monkeypatch, *now):
    class Frozen(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(*now, tzinfo=tz)

    monkeypatch.setattr(ime, "datetime", Frozen)
    monkeypatch.setattr(icalendar, "datetime", SimpleNamespace(datetime=Frozen))


def serve(monkeypatch, pages=None):
    pages = {
        ime.LISTING: "events.html",
        PARVATHY: "musicians-in-the-museum-parvathy-baul.html",
        f"{ime.BASE}?method=ical&id=17551": "17551.ics",
    } | (pages or {})
    fetched = []

    def get(url, headers=None, timeout=None):
        assert headers == ime.USER_AGENT_HEADERS
        fetched.append(url)
        return SimpleNamespace(text=(FIXTURES / pages[url]).read_text())

    monkeypatch.setattr(ime, "get_cached_session", lambda: SimpleNamespace(get=get))
    return fetched


@pytest.fixture(autouse=True)
def today(monkeypatch):
    freeze(monkeypatch, 2026, 11, 16)


def test_upcoming_event_takes_times_from_its_ical_export(monkeypatch):
    serve(monkeypatch)
    [event] = ime.events()
    assert event["name"] == "Musicians in the Museum: Parvathy Baul"
    assert event["url"] == PARVATHY
    assert event["startDate"] == "2026-11-21T11:30:00+05:30"
    assert event["endDate"] == "2026-11-21T19:00:00+05:30"
    assert event["location"] == ime.MUSEUM
    assert event["image"].endswith("/thumb-parvathy-baul-6af8571cb9b65.webp")


def test_description_drops_divi_shortcodes(monkeypatch):
    serve(monkeypatch)
    [event] = ime.events()
    assert event["description"].startswith("Vasu Dixit, Composer & Musician in Conversation")
    assert event["description"].endswith("Free to attend with RSVP")
    assert "[et_pb" not in event["description"]


def test_ical_labels_hash_id_and_language_guess_are_dropped(monkeypatch):
    serve(monkeypatch)
    [event] = ime.events()
    # The bio mentions Kannada poetry, which the iCal helper reads as the language
    assert not {"keywords", "inLanguage", "@id"} & event.keys()


def test_past_events_are_not_fetched(monkeypatch):
    fetched = serve(monkeypatch)
    ime.events()
    assert fetched == [ime.LISTING, PARVATHY, f"{ime.BASE}?method=ical&id=17551"]


def test_event_without_calendar_link_is_skipped(monkeypatch, capsys):
    serve(monkeypatch, {PARVATHY: "events.html"})
    assert ime.events() == []
    assert f"[IME] No calendar link: {PARVATHY}" in capsys.readouterr().out


def test_other_venues_keep_their_own_place():
    assert ime.place({"name": "The Humming Tree ", "address": "Indiranagar"}) == {
        "@type": "Place",
        "name": "The Humming Tree",
        "address": "Indiranagar",
    }
    assert ime.place({"@type": "Place", "name": "", "address": ""}) == ime.MUSEUM
    assert ime.place({"name": "IME Museum"}) == ime.MUSEUM
