import json
import sqlite3
from pathlib import Path

import pytest

from src import tagger

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
    expected = FIXTURES / "sports_screening.expected.json"
    assert got == json.loads(expected.read_text())
