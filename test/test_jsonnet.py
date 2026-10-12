import datetime
import json
import pathlib
import runpy
import shutil
import sys

import pytest

SCRIPT = "src/jsonnet.py"
FIXTURES = "test/fixtures/jsonnet"


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    (tmp_path / "transform").mkdir()
    (tmp_path / "out").mkdir()
    shutil.copy(f"{FIXTURES}/cksl.transform.jsonnet", tmp_path / "transform/cksl.jsonnet")
    shutil.copy(f"{FIXTURES}/cksl.jsonnet", tmp_path / "out/cksl.jsonnet")
    script = str(pathlib.Path(SCRIPT).resolve())
    monkeypatch.chdir(tmp_path)
    return script


def run(monkeypatch, script, path):
    monkeypatch.setattr(sys, "argv", [script, path])
    return runpy.run_path(script, run_name="__main__")


def freeze(monkeypatch, day):
    class Frozen(datetime.datetime):
        @classmethod
        def today(cls):
            return cls(*day)
    monkeypatch.setattr(datetime, "datetime", Frozen)


def test_transform_filters_and_maps_events(workdir, monkeypatch, capsys):
    freeze(monkeypatch, (2026, 2, 21))
    run(monkeypatch, workdir, "out/cksl.jsonnet")
    events = json.load(open("out/cksl.json"))
    assert sorted(e["startDate"] for e in events) == [
        "2026-02-21T18:00:00+05:30",
        "2026-02-22T10:00:00+05:30",
        "2026-02-28T18:00:00+05:30",
        "2026-03-01T22:00:00+05:30",
    ]
    e = next(e for e in events if e["@id"] == "cksl:145quj8q5dlmdfd1vs88nebsej")
    assert e["url"] == "https://cksl.in/?eid=145quj8q5dlmdfd1vs88nebsej#section3"
    assert e["description"] == "No further details available, please check with CKSL"
    assert e["location"]["name"] == "Choe Khor Sum Ling Centre, Ashwini"
    assert "[CKSL] 4 events (jsonnet.py)" in capsys.readouterr().out


def test_html2text_and_today_helpers(workdir, monkeypatch):
    freeze(monkeypatch, (2030, 1, 1))
    g = run(monkeypatch, workdir, "out/cksl.jsonnet")
    assert json.load(open("out/cksl.json")) == []
    assert g["today"]() == "2030-01-01"
    assert g["html2text"]('<p>Hi <a href="https://x.com">there</a></p>\n') == "Hi there"


def test_missing_input_exits(workdir, monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, workdir, "out/nope.jsonnet")
    assert exc.value.code == 1
    assert "Input out/nope.jsonnet not found" in capsys.readouterr().out


def test_missing_transform_raises(workdir, monkeypatch):
    shutil.copy("out/cksl.jsonnet", "out/other.jsonnet")
    with pytest.raises(Exception, match="Could not find transform/other.jsonnet"):
        run(monkeypatch, workdir, "out/other.jsonnet")
