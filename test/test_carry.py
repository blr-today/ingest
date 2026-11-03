import datetime
import json
import sqlite3

from src import carry
from src.common.tz import IST

NOW = datetime.datetime(2026, 11, 3, 18, 0, tzinfo=IST)


def db(path, events):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE events (url TEXT, event_json TEXT, id TEXT)")
    conn.executemany("INSERT INTO events (url, event_json) VALUES (?, ?)", [(e["url"], json.dumps(e)) for e in events])
    conn.commit()
    return path


def event(url, keywords, start, end=None):
    return {"url": url, "keywords": keywords, "startDate": start} | ({"endDate": end} if end else {})


def urls(path):
    return sorted(u for (u,) in sqlite3.connect(path).execute("SELECT url FROM events"))


def test_carries_upcoming_events_for_missing_tags(tmp_path):
    previous = db(tmp_path / "previous.db", [
        event("d/over", ["DISTRICT"], "2026-11-03T17:00:00+05:30"),
        event("d/tonight", "All,DISTRICT", "2026-11-03T13:30:00.000Z"),
        event("d/running", ["DISTRICT"], "2026-10-01", "2026-11-03"),
        event("b/play", ["BOOKMYSHOW"], "2026-11-04T19:30"),
        event("venue/talk", ["SABHA", "BOOKMYSHOW"], "2026-11-05T19:30"),
        event("u/walk", ["URBANAUT"], "2026-11-05T07:00"),
        event("d/undated", ["DISTRICT"], ""),
    ])
    current = db(tmp_path / "events.db", [
        event("b/other", ["BOOKMYSHOW"], "2026-11-06T19:30"),
        event("venue/talk", ["SABHA"], "2026-11-05T19:30"),
    ])
    lost, count = carry.carry(str(previous), {"DISTRICT", "BOOKMYSHOW"}, NOW, current)
    assert lost == {"DISTRICT"}
    assert count == 2
    assert urls(current) == ["b/other", "d/running", "d/tonight", "venue/talk"]


def test_any_missing_tag_restores_and_no_file_is_fine(tmp_path):
    previous = db(tmp_path / "previous.db", [
        event("venue/play", ["SABHA", "BOOKMYSHOW"], "2026-11-05T19:30"),
        event("d/gig", ["DISTRICT"], "2026-11-05T19:30"),
    ])
    current = db(tmp_path / "events.db", [])
    assert carry.carry(str(tmp_path / "missing.db"), {"BOOKMYSHOW"}, NOW, current) == ({"BOOKMYSHOW"}, 0)
    assert carry.carry(str(previous), {"BOOKMYSHOW", "DISTRICT"}, NOW, current)[1] == 2
    assert carry.carry(str(previous), {"BOOKMYSHOW", "DISTRICT"}, NOW, current) == (set(), 0)
