import json
import sqlite3
from pathlib import Path

import pytest

from src import tagger
from src.processors.__main__ import should_process_url
from src.processors.allevents import AllEvents
from src.processors.eventtype import EventType

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "test/fixtures/postbuild"

pytestmark = pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 38), reason="post-build.sql needs ->>"
)


def rows(db):
    with sqlite3.connect(db) as conn:
        found = conn.execute("SELECT url, event_json FROM events ORDER BY rowid")
        return {url: json.loads(event) for url, event in found}


def postbuild(events, db):
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE events (url TEXT, event_json TEXT)")
        conn.executemany(
            "INSERT INTO events VALUES (?, ?)",
            [(e["url"], json.dumps(e)) for e in events],
        )
        conn.executescript((REPO / "post-build.sql").read_text())
    return rows(db)


def tag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(tagger, "CACHE", tmp_path / "activities.sqlite")
    tagger.main()
    return rows(tmp_path / "events.db")


def test_sports_screening(tmp_path, monkeypatch):
    events = json.loads((FIXTURES / "sports_screening.json").read_text())
    postbuild(events, tmp_path / "events.db")
    got = {url: sorted(e["keywords"]) for url, e in tag(tmp_path, monkeypatch).items()}
    # SQL once tagged low-quality too; the tagger skips events with EXCLUDE tags
    expected = FIXTURES / "sports_screening.expected.json"
    assert got == json.loads(expected.read_text())


def test_allevents_rows_keep_eventtype_types(tmp_path):
    events = json.loads((FIXTURES / "allevents.json").read_text())
    for event in events:
        for processor in (AllEvents, EventType):
            assert should_process_url(processor, event["url"])
            processor.process(event["url"], event)
    got = postbuild(events, tmp_path / "events.db")
    assert [e.get("@type") for e in got.values()] == [
        "SocialEvent",
        "MusicEvent",
        "Event",
        "BusinessEvent",
    ]


def test_city_wide_venues_lose_their_geo(tmp_path):
    def event(url, name, lat, lng):
        geo = {"latitude": lat, "longitude": lng}
        return {
            "url": url,
            "name": "Run",
            "keywords": [],
            "location": {"name": name, "geo": geo},
        }

    got = postbuild(
        [
            event("https://a.in/1", "Bengaluru", 13.25, 77.71),
            event("https://a.in/2", "", 12.9628957, 77.57754),
            event("https://a.in/3", "Cubbon Park", 12.97425, 77.59219),
        ],
        tmp_path / "events.db",
    )
    assert [bool(e["location"].get("geo")) for e in got.values()] == [
        False,
        False,
        True,
    ]


def test_bms_craft_menus_are_low_quality(tmp_path):
    def bms(name, venue, start="2026-10-24T12:00:00+05:30", kind="EducationEvent"):
        return {
            "url": f"https://in.bookmyshow.com/events/{name}/ET1",
            "@type": kind,
            "name": name,
            "startDate": start,
            "location": {"name": venue},
            "keywords": ["BOOKMYSHOW"],
        }

    bar = "21st Amendment Gastrobar: Indiranagar"
    menu = [bms(n, bar) for n in ("sip-and-paint", "clay-lighter", "kintsugi")]
    alone = [
        bms("pottery", "Clay Station"),
        bms("resin", "Clay Station"),
        bms("later", bar, start="2026-10-24T15:00:00+05:30"),
        bms("comedy", bar, kind="ComedyEvent"),
    ]
    got = postbuild(menu + alone, tmp_path / "events.db")
    low = {e["name"] for e in got.values() if "LOW-QUALITY" in e["keywords"]}
    assert low == {"sip-and-paint", "clay-lighter", "kintsugi"}


def test_odyssey_vibes_venue_is_low_quality(tmp_path):
    event = {
        "url": "https://in.bookmyshow.com/events/open-talk-with-nishi/ET00386447",
        "name": "Candid Conversations with Nishi",
        "location": {"name": "Odyssey Vibes: Bengaluru"},
        "keywords": ["BOOKMYSHOW"],
    }
    got = postbuild([event], tmp_path / "events.db")
    assert "LOW-QUALITY" in got[event["url"]]["keywords"]


def test_small_world_is_low_quality(tmp_path):
    def bms(code, description):
        return {
            "url": f"https://in.bookmyshow.com/events/{code}",
            "description": description,
            "keywords": ["BOOKMYSHOW"],
        }

    events = [
        bms("perfumery/ET00469072", "Join Small World for a perfumery session"),
        bms("couple-dance-workshop/ET00417785", "Discover the Joy of Partner Dancing"),
        bms("songs/ET1", "Songs about a small world"),
    ]
    got = postbuild(events, tmp_path / "events.db")
    low = [url for url, e in got.items() if "LOW-QUALITY" in e["keywords"]]
    assert low == [e["url"] for e in events[:2]]
