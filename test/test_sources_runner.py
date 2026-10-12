import json
import runpy
import sys
from types import ModuleType

import pytest

from src.sources import __main__ as runner


@pytest.fixture
def source(tmp_path, monkeypatch):
    module = ModuleType("src.sources.fake")
    monkeypatch.setitem(sys.modules, "src.sources.fake", module)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    return module


def test_writes_events_and_count(source, tmp_path, capsys):
    source.events = lambda: [{"name": "Café", "url": "https://x.com/e"}, {"name": "B"}]
    assert runner.run("fake") == 0
    text = (tmp_path / "out/fake.json").read_text(encoding="utf-8")
    assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"
    assert '"Café"' in text
    assert capsys.readouterr().out == "[FAKE] 2 events\n"
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["fake.json"]


def test_empty_list_is_written(source, tmp_path, capsys):
    source.events = lambda: []
    assert runner.run("fake") == 0
    assert (tmp_path / "out/fake.json").read_text() == "[]\n"
    assert "[FAKE] 0 events" in capsys.readouterr().out


def test_failure_keeps_previous_file(source, tmp_path, capsys):
    (tmp_path / "out/fake.json").write_text("[1]")

    def events():
        raise ValueError("site down")
    source.events = events
    assert runner.run("fake") == 1
    assert (tmp_path / "out/fake.json").read_text() == "[1]"
    out, err = capsys.readouterr()
    assert out == ""
    assert "[FAKE] FAILED: ValueError: site down" in err
    assert "Traceback" in err


@pytest.mark.parametrize("result", [None, {"name": "A"}, ["https://x.com/e"]])
def test_non_list_result_fails(source, tmp_path, capsys, result):
    source.events = lambda: result
    assert runner.run("fake") == 1
    assert not (tmp_path / "out/fake.json").exists()
    assert "[FAKE] FAILED: TypeError" in capsys.readouterr().err


def test_unserialisable_events_leave_no_temp_file(source, tmp_path):
    (tmp_path / "out/fake.json").write_text("[1]")
    source.events = lambda: [{"when": object()}]
    assert runner.run("fake") == 1
    assert [p.name for p in (tmp_path / "out").iterdir()] == ["fake.json"]
    assert (tmp_path / "out/fake.json").read_text() == "[1]"


def test_unknown_source_fails(source, capsys):
    assert runner.run("nope") == 1
    assert "[NOPE] FAILED: ModuleNotFoundError" in capsys.readouterr().err


@pytest.mark.filterwarnings("ignore:.*found in sys.modules:RuntimeWarning")
def test_command_line(source, tmp_path, monkeypatch, capsys):
    source.events = lambda: [{"name": "A"}]
    monkeypatch.setattr(sys, "argv", ["src.sources", "fake"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("src.sources", run_name="__main__")
    assert exc.value.code == 0
    assert json.loads((tmp_path / "out/fake.json").read_text()) == [{"name": "A"}]
    monkeypatch.setattr(sys, "argv", ["src.sources"])
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("src.sources", run_name="__main__")
    assert exc.value.code == runner.USAGE
