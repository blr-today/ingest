import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.common import icalendar
from src.sources import ime

FIXTURES = Path(__file__).parent / "fixtures" / "ime"
EVENTS = "https://indianmusicexperience.org/mec-events/"
PARVATHY = EVENTS + "musicians-in-the-museum-parvathy-baul/"
GURU_NANAK = EVENTS + "guru-nanak-the-mystic-the-poet/"
PARVATHY_ICS = f"{ime.BASE}?method=ical&id=17551"
PAGES = {
    ime.LISTING: "events.html",
    PARVATHY: "musicians-in-the-museum-parvathy-baul.html",
    PARVATHY_ICS: "17551.ics",
    GURU_NANAK: "guru-nanak-the-mystic-the-poet.html",
    f"{ime.BASE}?method=ical&id=17540": "17540.ics",
}


def page(url, old=None, new=None):
    text = (FIXTURES / PAGES[url]).read_text()
    if old is not None:
        assert old in text
        text = text.replace(old, new)
    return text


@pytest.fixture(autouse=True)
def today(monkeypatch):
    class Frozen(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(2026, 11, 16, tzinfo=tz)

    monkeypatch.setattr(ime, "datetime", Frozen)
    monkeypatch.setattr(icalendar, "datetime", SimpleNamespace(datetime=Frozen))


def serve(monkeypatch, **served):
    """served maps a url to its text, or to an exception to raise"""
    fetched = []

    def get(url, headers=None, timeout=None):
        assert headers == ime.USER_AGENT_HEADERS
        fetched.append(url)
        body = served.get(url) or page(url)
        if isinstance(body, Exception):
            raise body
        return SimpleNamespace(text=body, raise_for_status=lambda: None)

    monkeypatch.setattr(ime, "get_cached_session", lambda: SimpleNamespace(get=get))
    return fetched


def by_url(monkeypatch, **served):
    serve(monkeypatch, **served)
    return {e["url"]: e for e in ime.events()}


def test_times_come_from_the_ical_export(monkeypatch):
    events = by_url(monkeypatch)
    parvathy, guru_nanak = events[PARVATHY], events[GURU_NANAK]
    assert parvathy["name"] == "Musicians in the Museum: Parvathy Baul"
    assert parvathy["startDate"] == "2026-11-21T11:30:00+05:30"
    assert parvathy["location"] == ime.MUSEUM
    assert parvathy["image"].endswith("/thumb-parvathy-baul-6af8571cb9b65.webp")
    # The page shows "5:00 pm - 7:00 pm", so the iCal end is real
    assert guru_nanak["endDate"] == "2026-11-22T19:00:00+05:30"
    # The page shows only "11:30 am"; the iCal export still ends it at 7 PM
    assert "endDate" not in parvathy


def test_ical_end_is_kept_when_the_page_shows_no_lone_start(monkeypatch):
    shown = page(PARVATHY, ">11:30 am<", ">All Day<")
    assert by_url(monkeypatch, **{PARVATHY: shown})[PARVATHY]["endDate"] == "2026-11-21T19:00:00+05:30"


def test_multi_day_event_keeps_its_end(monkeypatch):
    ics = page(PARVATHY_ICS, "DTEND;TZID=Asia/Kolkata:20261121", "DTEND;TZID=Asia/Kolkata:20261230")
    assert by_url(monkeypatch, **{PARVATHY_ICS: ics})[PARVATHY]["endDate"] == "2026-12-30T19:00:00+05:30"


def test_description_drops_divi_shortcodes(monkeypatch):
    description = by_url(monkeypatch)[PARVATHY]["description"]
    assert description.startswith("Vasu Dixit, Composer & Musician in Conversation")
    assert description.endswith("Free to attend with RSVP")
    assert "[et_pb" not in description


def test_ical_labels_hash_id_and_language_guess_are_dropped(monkeypatch):
    for event in by_url(monkeypatch).values():
        # The bio mentions Kannada poetry, which the iCal helper reads as the language
        assert not {"keywords", "inLanguage", "@id"} & event.keys()


def test_past_events_are_not_fetched(monkeypatch):
    fetched = serve(monkeypatch)
    ime.events()
    assert fetched == list(PAGES)


def test_event_without_calendar_link_is_skipped(monkeypatch, capsys):
    assert list(by_url(monkeypatch, **{PARVATHY: "<html></html>"})) == [GURU_NANAK]
    assert f"[IME] No calendar link: {PARVATHY}" in capsys.readouterr().out


def test_one_failing_event_does_not_drop_the_others(monkeypatch, capsys):
    events = by_url(monkeypatch, **{PARVATHY_ICS: TimeoutError("timed out")})
    assert list(events) == [GURU_NANAK]
    assert f"[IME] Skipping {PARVATHY}: TimeoutError: timed out" in capsys.readouterr().out


def test_listing_without_events_fails_the_source(monkeypatch):
    # A failed source keeps the last out/ime.json; an empty one would wipe IME
    serve(monkeypatch, **{ime.LISTING: "<html></html>"})
    with pytest.raises(ValueError, match="No events"):
        ime.events()


def test_place():
    assert ime.place({"name": "The Humming Tree ", "address": "Indiranagar"}) == {
        "@type": "Place",
        "name": "The Humming Tree",
        "address": "Indiranagar",
    }
    assert ime.place({"@type": "Place", "name": "", "address": ""}) == ime.MUSEUM
    assert ime.place({"name": None, "address": None}) == ime.MUSEUM
