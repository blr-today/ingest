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
PAGES = {
    ime.LISTING: "events.html",
    PARVATHY: "musicians-in-the-museum-parvathy-baul.html",
    f"{ime.BASE}?method=ical&id=17551": "17551.ics",
    GURU_NANAK: "guru-nanak-the-mystic-the-poet.html",
    f"{ime.BASE}?method=ical&id=17540": "17540.ics",
}


def freeze(monkeypatch, *now):
    class Frozen(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(*now, tzinfo=tz)

    monkeypatch.setattr(ime, "datetime", Frozen)
    monkeypatch.setattr(icalendar, "datetime", SimpleNamespace(datetime=Frozen))


def serve(monkeypatch, pages=None):
    pages = PAGES | (pages or {})
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


def by_url(monkeypatch, pages=None):
    serve(monkeypatch, pages)
    return {e["url"]: e for e in ime.events()}


def test_upcoming_event_takes_its_start_from_the_ical_export(monkeypatch):
    event = by_url(monkeypatch)[PARVATHY]
    assert event["name"] == "Musicians in the Museum: Parvathy Baul"
    assert event["startDate"] == "2026-11-21T11:30:00+05:30"
    assert event["location"] == ime.MUSEUM
    assert event["image"].endswith("/thumb-parvathy-baul-6af8571cb9b65.webp")


def test_end_shown_on_the_page_is_kept(monkeypatch):
    event = by_url(monkeypatch)[GURU_NANAK]
    assert event["startDate"] == "2026-11-22T17:00:00+05:30"
    assert event["endDate"] == "2026-11-22T19:00:00+05:30"


def test_filler_ical_end_is_dropped_when_the_page_shows_only_a_start(monkeypatch):
    # The page says "11:30 am"; the iCal export still ends it at 7 PM
    assert "endDate" not in by_url(monkeypatch)[PARVATHY]


@pytest.mark.parametrize(
    "time",
    [None, "All Day", ""],
    ids=["no time block", "all day", "blank"],
)
def test_ical_end_is_kept_unless_the_page_shows_a_lone_start(monkeypatch, tmp_path, time):
    page = '<a href="https://indianmusicexperience.org/?method=ical&#038;id=17551">iCal</a>'
    if time is not None:
        page = f'<div class="mec-single-event-time"><abbr class="mec-events-abbr">{time}</abbr></div>' + page
    (tmp_path / "page.html").write_text(page)
    event = by_url(monkeypatch, {PARVATHY: str(tmp_path / "page.html")})[PARVATHY]
    assert event["endDate"] == "2026-11-21T19:00:00+05:30"


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
    assert list(by_url(monkeypatch, {PARVATHY: "events.html"})) == [GURU_NANAK]
    assert f"[IME] No calendar link: {PARVATHY}" in capsys.readouterr().out


def test_other_venues_keep_their_own_place():
    assert ime.place({"name": "The Humming Tree ", "address": "Indiranagar"}) == {
        "@type": "Place",
        "name": "The Humming Tree",
        "address": "Indiranagar",
    }
    assert ime.place({"@type": "Place", "name": "", "address": ""}) == ime.MUSEUM
    assert ime.place({"name": "IME Museum"}) == ime.MUSEUM
