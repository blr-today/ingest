import json
import pathlib
import runpy
import shutil
import sqlite3
import sys

import pytest

from src import build

SCRIPT = str(pathlib.Path("src/build.py").resolve())
FIXTURE = pathlib.Path("test/fixtures/build/mapindia.json").resolve()


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    (tmp_path / "out").mkdir()
    shutil.copy(FIXTURE, tmp_path / "out/mapindia.json")
    (tmp_path / "out/manual.json").write_text(json.dumps([{"name": "No link", "keywords": ["X"]}]))
    monkeypatch.chdir(tmp_path)
    return tmp_path


def rows():
    conn = sqlite3.connect("events.db")
    got = conn.execute("SELECT url, event_json FROM events").fetchall()
    conn.close()
    return [(url, json.loads(e)) for url, e in got]


def test_create_table_and_insert(workdir):
    build.create_events_table()
    build.create_events_table()
    conn = sqlite3.connect("events.db")
    build.insert_event_json(conn, "https://x.com/e", {"name": "E", "keywords": ["A"]})
    conn.commit()
    conn.close()
    assert rows() == [("https://x.com/e", {"name": "E", "keywords": ["A"]})]


def test_local_events_are_tagged_with_their_file(workdir, capsys):
    got = list(build.fetch_local_events())
    assert [url for url, _ in got] == [
        "https://map-india.org/map-events/drawing-the-everyday/",
        "https://map-india.org/map-events/book-launch-imposter-the-playful-subversions-of-orijit-sen/",
        "https://map-india.org/map-events/make-your-own-superhero/",
    ]
    assert sorted(got[0][1]["keywords"]) == ["CBD", "MAP", "MAPINDIA", "Workshops"]
    assert "Event in out/manual.json has no URL" in capsys.readouterr().out


def test_local_events_file_filter(workdir):
    assert list(build.fetch_local_events("out/manual.json")) == []
    assert len(list(build.fetch_local_events("out/mapindia.json"))) == 3


def test_main_loads_only_json_files(workdir, monkeypatch):
    many = [{"url": f"https://r.com/{i}", "name": f"R{i}"} for i in range(11)]
    (workdir / "out/many.json").write_text(json.dumps(many))
    (workdir / "out/stale.txt").write_text("https://r.com/listed\n")
    monkeypatch.setattr(sys, "argv", [SCRIPT])
    runpy.run_path(SCRIPT, run_name="__main__")
    got = dict(rows())
    assert len(got) == 14
    assert got["https://r.com/0"] == {"url": "https://r.com/0", "name": "R0", "keywords": ["MANY"]}
    assert "https://map-india.org/map-events/make-your-own-superhero/" in got
    assert "https://r.com/listed" not in got


def test_main_passes_file_filter(workdir, monkeypatch):
    monkeypatch.setattr(sys, "argv", [SCRIPT, "out/manual.json"])
    runpy.run_path(SCRIPT, run_name="__main__")
    assert rows() == []
    monkeypatch.setattr(sys, "argv", [SCRIPT, "out/mapindia.json"])
    runpy.run_path(SCRIPT, run_name="__main__")
    assert len(rows()) == 3
