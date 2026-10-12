import importlib
import json
import pkgutil
import sqlite3
from pathlib import Path

import pytest

from src.processors import ignored_events, koota, lastcall, patch, registry, venues
from src.processors.__main__ import process_events, should_process_url
from src.processors.base import Processor
from src.processors.highape import HighApe
from src.processors.registry import PROCESSORS
from src.processors.schemafixer import SchemaFixer

ROWS = json.loads(
    (Path(__file__).parent / "fixtures/processors/events.json").read_text()
)
CACHED = (patch.get_patch, venues.venues, lastcall.slot_totals)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(koota, "fetch_record", lambda url: None)


@pytest.fixture
def build(tmp_path, monkeypatch):
    (tmp_path / "patch").mkdir()
    (tmp_path / "patch/venues.json").write_text("[]")
    (tmp_path / "patch/highape.com.json").write_text(
        '{"keywords": ["HIGHAPE"], "inLanguage": "en"}'
    )
    conn = sqlite3.connect(tmp_path / "events.db")
    conn.execute("CREATE TABLE events (url TEXT, event_json TEXT)")
    conn.commit()
    monkeypatch.chdir(tmp_path)
    for f in CACHED:
        f.cache_clear()
    yield conn
    for f in CACHED:
        f.cache_clear()


def run(conn, rows):
    conn.executemany("INSERT INTO events VALUES (?, ?)", rows)
    conn.commit()
    process_events()
    return dict(conn.execute("SELECT url, event_json FROM events"))


def test_base_processor_does_nothing():
    assert Processor.process("u", {"name": "x"}) is None


def test_registry_order():
    assert [p.__name__ for p in PROCESSORS] == [
        "Koota", "SchemaFixer", "Costly", "BookMyShow", "Exhibition",
        "GeoProcessor", "AllEvents", "BhaagoIndia", "District", "HighApe",
        "IgnoredEvents", "ScriptLanguage", "Patch", "Venues", "EventType",
        "Cost", "LastCall",
    ]


def test_every_processor_is_registered():
    names = [m.name for m in pkgutil.iter_modules([Path(registry.__file__).parent])]
    found = {
        obj
        for name in names
        for obj in vars(importlib.import_module(f"src.processors.{name}")).values()
        if isinstance(obj, type) and issubclass(obj, Processor) and obj is not Processor
    }
    assert found == set(PROCESSORS) and len(found) == len(PROCESSORS)


def test_url_filters():
    assert should_process_url(HighApe, "https://www.highape.com/bangalore/events/x")
    assert not should_process_url(HighApe, "https://district.in/events/x")
    assert should_process_url(SchemaFixer, "https://anything.example/")


def test_scraped_events_are_processed(build):
    events = {
        u: json.loads(e)
        for u, e in run(build, [(u, json.dumps(e)) for u, e in ROWS]).items()
    }
    koota = events[ROWS[0][0]]
    assert (koota["startDate"], koota["endDate"]) == (
        "2026-10-25T12:00:00+05:30",
        "2026-10-25T13:30:00+05:30",
    )
    assert koota["@context"] == "https://schema.org"
    district = events[ROWS[1][0]]
    assert district["startDate"] == "2026-10-11T14:00:00+05:30"
    assert district["keywords"] == ["Modular Type Workshop by A Letter Atelier", "All"]
    # A two-lakh rupee tour is dropped by Costly
    assert ROWS[2][0] not in events
    assert events[ROWS[3][0]] == ROWS[3][1] | {"keywords": []}


def test_ignored_events_are_deleted(build, monkeypatch):
    monkeypatch.setattr(ignored_events, "IGNORED_EVENT_UIDS", [ROWS[0][1]["@id"]])
    events = run(build, [(u, json.dumps(e)) for u, e in ROWS])
    assert ROWS[0][0] not in events and ROWS[1][0] in events


def test_bad_rows_are_skipped(build, caplog):
    url, event = ROWS[1]
    rows = [("https://x.in/nodate", '{"name": "x"}'), ("https://x.in/bad", "{oops")]
    rows += [(f"{url}#{i}", json.dumps(event)) for i in range(21)]
    events = run(build, rows)
    assert json.loads(events["https://x.in/nodate"])["name"] == "x"
    assert events["https://x.in/bad"] == "{oops"
    starts = [json.loads(e)["startDate"] for u, e in events.items() if "#" in u]
    assert starts == ["2026-10-11T14:00:00+05:30"] * 21
    assert "Error processing event at URL https://x.in/bad" in caplog.text
    assert json.loads(events["https://x.in/nodate"])["@context"] == "https://schema.org"
    assert "Error in processor" not in caplog.text
