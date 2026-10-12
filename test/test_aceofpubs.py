import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from src.sources import aceofpubs
from src.sources.aceofpubs import clean, event_urls, in_bangalore, page_event, upcoming

FIXTURES = Path(__file__).parent / "fixtures/aceofpubs"
BADMAASH = "https://aceofpubs.com/events/bollywood-trivia-badmaash-sarjapur-bengaluru/"
WHITEFIELD = "https://aceofpubs.com/events/monaco-gp-screening-trivia-night-whitefield-social/"
MONASTERY = "https://aceofpubs.com/events/trivia-night-monastery-hyd/"


def fake_get(url, headers=None, timeout=None):
    name = "sitemap.xml" if url == aceofpubs.SITEMAP else url.rstrip("/").split("/")[-1] + ".html"
    return SimpleNamespace(text=(FIXTURES / name).read_text())


SESSION = SimpleNamespace(get=fake_get)


def freeze(monkeypatch, *args):
    class Fixed(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(*args, tzinfo=tz)

    monkeypatch.setattr(aceofpubs, "datetime", SimpleNamespace(datetime=Fixed, timezone=datetime.timezone))


def test_event_urls_from_sitemap():
    assert event_urls(SESSION) == [MONASTERY, WHITEFIELD, BADMAASH]


def test_page_event_reads_jsonld():
    event = page_event(SESSION, MONASTERY)
    assert event["name"] == "Trivia Night @ Monastery (Hyd)"
    assert event["location"]["address"]["addressLocality"] == "Hyderabad"


def test_in_bangalore():
    assert in_bangalore(page_event(SESSION, BADMAASH))
    assert in_bangalore(page_event(SESSION, WHITEFIELD))
    assert not in_bangalore(page_event(SESSION, MONASTERY))


def test_clean_fixes_placeholders():
    event = clean(page_event(SESSION, BADMAASH), BADMAASH)
    assert event["name"] == "Bollywood Trivia @ Badmaash (Sarjapur)"
    assert event["url"] == BADMAASH
    assert event["organizer"]["name"] == "Ace of Pubs"
    assert "performer" not in event and "previousStartDate" not in event
    assert event["eventStatus"] == "https://schema.org/EventScheduled"
    assert event["location"]["address"]["addressRegion"] == "Karnataka"


def test_clean_unescapes_name():
    event = clean(page_event(SESSION, WHITEFIELD), WHITEFIELD)
    assert event["name"] == "Austrian GP Screening & Trivia Night @ Whitefield SOCIAL"


def test_upcoming(monkeypatch):
    freeze(monkeypatch, 2026, 9, 1)
    assert upcoming({"endDate": "2026-09-30T22:00:00+05:30"})
    assert upcoming({"startDate": "2026-09-30T20:00:00+05:30"})
    assert not upcoming({"endDate": "2026-06-28T20:30:00+05:30"})
    assert not upcoming({"endDate": "soon"})
    assert not upcoming({})


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_events_keep_upcoming_bangalore_events(monkeypatch):
    monkeypatch.setattr(aceofpubs, "get_cached_session", lambda: SESSION)
    real_datetime = datetime.datetime

    class Fixed(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return real_datetime(2026, 9, 1, tzinfo=tz)

    monkeypatch.setattr(datetime, "datetime", Fixed)
    [event] = aceofpubs.events()
    assert event["url"] == BADMAASH
