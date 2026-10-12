import datetime
import importlib
import json
import shutil

import pytest

from src import jsonnet

FIXTURES = "test/fixtures/jsonnet"
ICS = (
    "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:test\r\nBEGIN:VEVENT\r\nUID:1@test\r\n"
    "DTSTAMP:20300101T000000Z\r\nDTSTART:20300101T120000Z\r\nDTEND:20300101T130000Z\r\n"
    "SUMMARY:Meditation\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"
)


@pytest.fixture
def raw(tmp_path, monkeypatch):
    (tmp_path / "transform").mkdir()
    shutil.copy(f"{FIXTURES}/cksl.transform.jsonnet", tmp_path / "transform/cksl.jsonnet")
    with open(f"{FIXTURES}/cksl.jsonnet") as f:
        text = f.read()
    monkeypatch.chdir(tmp_path)
    return text


def freeze(monkeypatch, day):
    class Frozen(datetime.datetime):
        @classmethod
        def today(cls):
            return cls(*day)
    monkeypatch.setattr(datetime, "datetime", Frozen)


def test_transform_filters_and_maps_events(raw, monkeypatch):
    freeze(monkeypatch, (2026, 2, 21))
    events = jsonnet.transform("cksl", raw)
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


def test_html2text_and_today_helpers(raw, monkeypatch):
    freeze(monkeypatch, (2030, 1, 1))
    assert jsonnet.transform("cksl", raw) == []
    assert jsonnet.today() == "2030-01-01"
    assert jsonnet.html2text('<p>Hi <a href="https://x.com">there</a></p>\n') == "Hi there"


def test_missing_transform_raises(raw):
    with pytest.raises(Exception, match="Could not find transform/other.jsonnet"):
        jsonnet.transform("other", raw)


@pytest.mark.parametrize("stem", ["te", "tpcc", "cksl"])
def test_sources_pass_their_raw_file(stem, tmp_path, monkeypatch):
    module = importlib.import_module(f"src.sources.{stem}")
    (tmp_path / "out").mkdir()
    (tmp_path / f"out/{stem}.jsonnet").write_text('{"raw": 1}')
    (tmp_path / "out/cksl.ics").write_text(ICS)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "transform", lambda name, text: [{"stem": name, "input": json.loads(text)}])
    [got] = module.events()
    assert got["stem"] == stem
    if stem == "cksl":
        assert [e["name"] for e in got["input"]] == ["Meditation"]
    else:
        assert got["input"] == {"raw": 1}
