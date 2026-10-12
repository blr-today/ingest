import json
import logging
import pathlib
import runpy
import sqlite3
import sys
from types import SimpleNamespace

import pytest

import validator
from validator import SchemaOrgValidator, ValidationResult

FIXTURE = pathlib.Path("test/fixtures/validator/events.json").resolve()
SCRIPT = str(pathlib.Path("src/validator.py").resolve())
CDN = "- https://map-india.org/\n- https://images.example.com/\n"


def events():
    return json.load(open(FIXTURE))


def no_network(url, options=None):
    raise RuntimeError(f"network disabled: {url}")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(validator.jsonld, "_default_document_loader", no_network)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)


def cdn(monkeypatch, text=CDN, error=None):
    def get(url, timeout=None):
        assert url == validator.IMAGE_CDN_URL
        if error:
            raise error
        return SimpleNamespace(text=text, raise_for_status=lambda: None)
    monkeypatch.setattr(validator.requests, "get", get)


def test_image_urls_accepts_strings_lists_and_objects():
    assert validator.image_urls({"image": "https://a.com/x.jpg"}) == ["https://a.com/x.jpg"]
    assert validator.image_urls({}) == []
    images = ["https://a.com/1.jpg", {"url": "https://b.com/2.jpg"}, {"@id": "#img"}, "/local.jpg", None]
    assert validator.image_urls({"image": images}) == ["https://a.com/1.jpg", "https://b.com/2.jpg"]


def test_unsupported_image_hosts_are_counted(monkeypatch):
    cdn(monkeypatch)
    urls = ["https://map-india.org/a.jpg", "https://x.com/1.jpg", "https://y.com/1.jpg", "https://x.com/2.jpg"]
    assert validator.unsupported_image_hosts(urls) == [
        ("x.com", 2, "https://x.com/2.jpg"),
        ("y.com", 1, "https://y.com/1.jpg"),
    ]
    assert validator.unsupported_image_hosts(urls[:1]) == []


def test_unsupported_image_hosts_without_cdn_list(monkeypatch):
    cdn(monkeypatch, error=ConnectionError("down"))
    assert validator.unsupported_image_hosts(["https://x.com/1.jpg"]) is None


def test_real_events_are_valid():
    v = SchemaOrgValidator()
    first, second, _ = events()
    for event in (first, second):
        result = v.validate_event(event, event["url"])
        assert result == ValidationResult(True, [], [], event["@type"], event["url"])
    assert v.stats == {"total": 2, "valid": 2, "invalid": 0, "warnings": 0}


def test_series_and_hackathons_are_valid():
    v = SchemaOrgValidator()
    for kind in ("EventSeries", "Hackathon"):
        event = events()[0] | {"@type": kind}
        assert v.validate_event(event, event["url"]).is_valid


def test_event_without_type_or_context_is_invalid():
    v = SchemaOrgValidator()
    result = v.validate_event(events()[2], "https://www.sofarsounds.com/events/67871")
    assert not result.is_valid
    assert result.errors == [
        "Invalid JSON-LD: missing required schema.org properties",
        "Schema error: '@type' is a required property",
    ]
    assert result.event_type is None
    assert v.stats["invalid"] == 1


def test_soft_schema_problems_are_warnings():
    v = SchemaOrgValidator()
    event = events()[0] | {"name": "", "image": {"url": "https://map-india.org/a.jpg"}}
    result = v.validate_event(event)
    assert result.is_valid
    assert len(result.warnings) == 2
    assert result.warnings[0] == "Schema warning: '' should be non-empty"
    assert v.stats == {"total": 1, "valid": 1, "invalid": 0, "warnings": 1}


def test_unknown_type_and_bad_dates_are_errors():
    event = events()[0] | {"@type": "Concert", "startDate": 20261017}
    errors = SchemaOrgValidator().validate_event(event).errors
    assert errors[0].startswith("Schema error: 'Concert' is not one of")
    assert errors[1] == "Schema error: 20261017 is not of type 'string'"


def test_jsonld_errors():
    v = SchemaOrgValidator()
    remote = events()[0] | {"@context": "http://schema.org"}
    assert v._validate_jsonld(remote) == []
    [error] = v._validate_jsonld(events()[0] | {"@context": 5})
    assert error.startswith("JSON-LD validation error:") and "@context must be an object" in error


def test_schema_validator_failure_is_an_error(monkeypatch):
    def broken(schema):
        raise ValueError("bad schema")
    monkeypatch.setattr(validator, "Draft7Validator", broken)
    assert SchemaOrgValidator()._validate_schema({}) == (["Schema validation failed: bad schema"], [])


def summary_results():
    bad = ValidationResult(False, ["Schema error: x"], [], "Concert", None)
    warn = ValidationResult(True, [], ["Schema warning: y"], "Event", "https://e.com/1")
    ok = ValidationResult(True, [], [], "Event", "https://e.com/2")
    return [(1, bad), (2, warn), (3, ok)]


def test_step_summary_needs_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    validator.write_github_step_summary({}, [], None)
    assert list(tmp_path.iterdir()) == []


def test_step_summary_report(tmp_path, monkeypatch):
    path = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))
    stats = {"total": 4, "valid": 3, "invalid": 1, "warnings": 1}
    validator.write_github_step_summary(stats, summary_results(), [("x.com", 2, "https://x.com/2.jpg")])
    text = path.read_text()
    assert "- **Total Events**: 4\n" in text
    assert "- **Valid Events**: 3 (75.0%)\n" in text
    assert "| x.com | 2 | https://x.com/2.jpg |\n" in text
    assert "### ❌ Unknown URL\n**Type**: Concert\n\n**Errors**:\n- Schema error: x\n" in text
    assert "### ⚠️ https://e.com/1\n**Type**: Event\n\n**Warnings**:\n- Schema warning: y\n" in text
    assert "https://e.com/2" not in text


def test_step_summary_image_host_states(tmp_path, monkeypatch):
    path = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(path))
    stats = {"total": 1, "valid": 1, "invalid": 0, "warnings": 0}
    validator.write_github_step_summary(stats, [], None)
    assert f"Could not fetch {validator.IMAGE_CDN_URL}" in path.read_text()
    validator.write_github_step_summary(stats, [], [])
    text = path.read_text()
    assert "All event images are served via the image CDN." in text
    assert "## Failed Events" not in text and "## Events with Warnings" not in text


@pytest.fixture
def events_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conn = sqlite3.connect("events.db")
    conn.execute("CREATE TABLE events (url TEXT, event_json TEXT)")
    rows = [(e["url"], json.dumps(e)) for e in events()]
    rows.append(("https://e.com/warn", json.dumps(events()[0] | {"name": ""})))
    rows.append(("https://e.com/broken", "{not json"))
    rows.append(("https://e.com/null", "null"))
    conn.executemany("INSERT INTO events VALUES (?, ?)", rows)
    conn.commit()
    conn.close()
    return tmp_path


def test_validate_all_events_writes_report(events_db, monkeypatch, caplog):
    cdn(monkeypatch)
    caplog.set_level(logging.INFO, logger="validator")
    results, stats = validator.validate_all_events("report.json", verbose=True)
    assert stats == {"total": 4, "valid": 3, "invalid": 1, "warnings": 1}
    assert [rowid for rowid, _ in results] == [1, 2, 3, 4]
    report = json.load(open("report.json"))
    assert report["stats"] == stats
    assert [r["url"] for r in report["results"]] == ["https://www.sofarsounds.com/events/67871", "https://e.com/warn"]
    assert "JSON error for https://e.com/broken" in caplog.text
    assert "Validation error for https://e.com/null" in caplog.text
    assert "sofar-sounds-live.imgix.net" in caplog.text


def test_validator_script(events_db, monkeypatch):
    cdn(monkeypatch, error=ConnectionError("down"))
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(events_db / "summary.md"))
    monkeypatch.setattr(sys, "argv", [SCRIPT, "-o", "out.json"])
    runpy.run_path(SCRIPT, run_name="__main__")
    assert json.load(open("out.json"))["stats"]["total"] == 4
    assert "Could not fetch" in (events_db / "summary.md").read_text()


def test_empty_database_reports_zero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    cdn(monkeypatch)
    sqlite3.connect("events.db").execute("CREATE TABLE events (url TEXT, event_json TEXT)")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary.md"))
    _, stats = validator.validate_all_events("report.json")
    assert stats["total"] == 0
    validator.write_github_step_summary(stats, [], [])
    assert "(0.0%)" in (tmp_path / "summary.md").read_text()
