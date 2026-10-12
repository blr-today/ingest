import datetime
import types

import pytest

from src.common import icalendar

BIC = "test/fixtures/icalendar/bic.ics"
MAP = "test/fixtures/icalendar/mapindia.ics"


def freeze(monkeypatch, *args):
    class Frozen(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(*args, tzinfo=tz)
    monkeypatch.setattr(icalendar, "datetime", types.SimpleNamespace(datetime=Frozen))


@pytest.fixture
def events(monkeypatch):
    freeze(monkeypatch, 2026, 10, 1)
    return lambda path: {e["name"]: e for e in icalendar.convert_ics_to_events(path)}


def write_ics(tmp_path, *vevents):
    body = "".join(f"BEGIN:VEVENT\r\nUID:{i}@test\r\nDTSTAMP:20261001T000000Z\r\n{v}END:VEVENT\r\n" for i, v in enumerate(vevents))
    path = tmp_path / "cal.ics"
    path.write_text(f"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:test\r\n{body}END:VCALENDAR\r\n")
    return str(path)


def test_plain_event_fields(events):
    e = events(BIC)["The Many Pasts of Panipat, 1761"]
    assert e["@type"] == "Event"
    assert e["@id"] == "94968-1791916200-1791921600@bangaloreinternationalcentre.org"
    assert e["startDate"] == "2026-10-13T18:30:00+05:30"
    assert e["endDate"] == "2026-10-13T20:00:00+05:30"
    assert e["url"] == "https://bangaloreinternationalcentre.org/event/the-many-pasts-of-panipat-1761/"
    assert e["keywords"] == ["History", "In Memory"]
    assert e["location"]["name"].startswith("Bangalore International Centre, 7, 4th Main Road")
    assert e["inLanguage"] == "en"
    assert e["image"] == "https://bangaloreinternationalcentre.org/wp-content/uploads/2026/09/Thumbnail-Panipat.jpg"


def test_music_performance(events):
    e = events(BIC)["Swarantar – A Mosaic of Melodies"]
    assert e["@type"] == "MusicEvent"
    assert e["workPerformed"] == {"@type": "CreativeWork", "name": "Swarantar – A Mosaic of Melodies"}


def test_subtitled_film_is_a_screening(events):
    e = events(BIC)["Marriage Cops"]
    assert e["@type"] == "ScreeningEvent"
    assert e["workPresented"] == {"@type": "Movie", "name": "Marriage Cops"}
    assert e["inLanguage"] == "hi"
    assert e["subtitleLanguage"] == "en"


def test_utc_times_and_workshops(events):
    got = events(MAP)
    assert len(got) == 3
    e = got["Drawing the Everyday"]
    assert e["@type"] == "EducationEvent"
    assert e["startDate"] == "2026-10-17T11:00:00+05:30"
    assert e["keywords"] == ["CBD", "MAP", "Workshops"]
    assert "location" not in e
    assert got["Book Launch - Imposter: The Playful Subversions of Orijit Sen"]["@type"] == "Event"


def test_past_events_are_dropped(monkeypatch):
    freeze(monkeypatch, 2026, 10, 17, 14)
    names = sorted(e["name"] for e in icalendar.convert_ics_to_events(MAP))
    assert names == [
        "Book Launch - Imposter: The Playful Subversions of Orijit Sen",
        "Make Your Own Superhero",
    ]


def test_events_without_end_last_two_hours(events, tmp_path):
    path = write_ics(tmp_path, "DTSTART:20261020T120000Z\r\nDTEND:20261020T120000Z\r\nSUMMARY:Talk\r\n")
    [e] = icalendar.convert_ics_to_events(path)
    assert e["endDate"] == "2026-10-20T19:30:00+05:30"
    assert e["description"] == "" and "keywords" not in e


def test_performance_categories(events, tmp_path):
    span = "DTSTART:20261020T120000Z\r\nDTEND:20261020T140000Z\r\n"
    path = write_ics(
        tmp_path,
        span + "SUMMARY:Play\r\nCATEGORIES:Performances\r\n",
        span + "SUMMARY:Gig\r\nCATEGORIES:Performances\r\nDESCRIPTION:live music\r\n",
        span + "SUMMARY:Hamlet\r\nCATEGORIES:Performing Arts,Theatre\r\n",
        span + "SUMMARY:Film\r\nCATEGORIES:Film Screenings\r\nDESCRIPTION:In Tamil with Kannada subtitles\r\n",
        span + "SUMMARY:Pic\r\nATTACH:http://example.com/a.jpg\r\nATTACH:https://example.com/b.jpg\r\n",
    )
    got = {e["name"]: e for e in icalendar.convert_ics_to_events(path)}
    assert got["Play"]["@type"] == "TheaterEvent"
    assert got["Gig"]["@type"] == "MusicEvent"
    assert got["Hamlet"]["@type"] == "TheaterEvent"
    assert got["Hamlet"]["workPerformed"] == {"@type": "TheaterPlay", "name": "Hamlet"}
    assert got["Film"]["@type"] == "ScreeningEvent"
    assert (got["Film"]["inLanguage"], got["Film"]["subtitleLanguage"]) == ("ta", "kn")
    assert got["Pic"]["image"] == "https://example.com/b.jpg"


def test_language_is_the_first_spoken_one(events, tmp_path):
    span = "DTSTART:20261020T120000Z\r\nDTEND:20261020T140000Z\r\n"
    path = write_ics(
        tmp_path,
        span + "SUMMARY:A\r\nDESCRIPTION:Hindi with Tamil subtitles\r\n",
        span + "SUMMARY:B\r\nDESCRIPTION:A Tamil play\\, adapted from Hindi\r\n",
        span + "SUMMARY:C\r\nDESCRIPTION:With Kannada Subtitles\r\n",
    )
    got = {e["name"]: e["inLanguage"] for e in icalendar.convert_ics_to_events(path)}
    assert got == {"A": "hi", "B": "ta", "C": "en"}
