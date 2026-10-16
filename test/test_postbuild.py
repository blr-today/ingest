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
