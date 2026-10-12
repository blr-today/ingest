import datetime
import json
import runpy
import sys
import types

import pytest

from common import icalendar

SCRIPT = "src/ics-to-event.py"
MAP = "test/fixtures/icalendar/mapindia.ics"


def run(monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", [SCRIPT, *args])
    runpy.run_path(SCRIPT, run_name="__main__")


def test_usage_needs_two_arguments(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        run(monkeypatch, MAP)
    assert exc.value.code == 1
    assert "Usage" in capsys.readouterr().out


def test_missing_or_empty_calendar_is_skipped(monkeypatch, capsys, tmp_path):
    empty = tmp_path / "empty.ics"
    empty.write_text("")
    out = tmp_path / "out.json"
    run(monkeypatch, str(tmp_path / "missing.ics"), str(out))
    run(monkeypatch, str(empty), str(out))
    assert capsys.readouterr().out.count("ICS Calendar is invalid or empty") == 2
    assert not out.exists()


def test_calendar_is_written_as_json(monkeypatch, capsys, tmp_path):
    class Frozen(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(2026, 10, 1, tzinfo=tz)
    monkeypatch.setattr(icalendar, "datetime", types.SimpleNamespace(datetime=Frozen))
    out = tmp_path / "mapindia.json"
    run(monkeypatch, MAP, str(out))
    events = json.loads(out.read_text())
    assert sorted(e["@id"] for e in events) == ["1418@map-india.org", "1419@map-india.org", "1420@map-india.org"]
    assert f"JSON data saved to {out}" in capsys.readouterr().out
