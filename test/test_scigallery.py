import datetime
import json
from pathlib import Path
from types import SimpleNamespace

import scigallery
from common.tz import IST
from scigallery import filter_data, get_performer_type, guess_event_type, parse_duration_hours, parse_timestamp

FIXTURES = Path(__file__).parent / "fixtures" / "scigallery"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def freeze(monkeypatch, *args):
    class FrozenDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(*args, tzinfo=IST)

    monkeypatch.setattr(scigallery, "datetime", SimpleNamespace(datetime=FrozenDatetime, timedelta=datetime.timedelta))


def upcoming(monkeypatch):
    freeze(monkeypatch, 2026, 10, 5)
    return {e["name"]: e for e in filter_data(load("programmes").values(), load("experts"))}


def test_helpers():
    assert guess_event_type("Curatorial Walkthrough") == "EducationEvent"
    assert guess_event_type("Film Screening") == "ScreeningEvent"
    assert guess_event_type("Book Launch and Discussion") == "Event"
    assert parse_duration_hours("1.5") == 1.5
    assert parse_duration_hours("") == 0.0
    assert parse_duration_hours(None) == 0.0
    assert get_performer_type("Dakshin Foundation") == "Organization"
    assert get_performer_type("CALORIE Film Festival") == "Organization"
    assert get_performer_type("Nikki Schuster") == "Person"
    assert parse_timestamp("2026-10-25T11:30:00.000Z").isoformat() == "2026-10-25T17:00:00+05:30"
    assert parse_timestamp("").year == 1900


def test_only_listed_upcoming_programmes(monkeypatch):
    assert sorted(upcoming(monkeypatch)) == [
        "D.D. Kosambi: One Life, Many Worlds",
        "Exploring the Molecular World",
        "The Bengaluru Uncertainty Principle",
    ]


def test_programme_on_site(monkeypatch):
    event = upcoming(monkeypatch)["The Bengaluru Uncertainty Principle"]
    assert event["@type"] == "EducationEvent"
    assert event["startDate"] == "2026-10-25T17:00:00+05:30"
    assert event["endDate"] == "2026-10-25T19:00:00+05:30"
    assert event["url"] == "https://quantum.scigalleryblr.org/programmes?p=the-bengaluru-uncertainty-principle"
    assert event["location"] == {
        "@type": "Place",
        "name": "Lecture Hall, Science Gallery Bengaluru",
        "address": "Science Gallery, Bangalore",
        "url": "https://maps.app.goo.gl/jwjGeJVgghfGSW4k9",
    }
    assert event["performer"] == [
        {"@type": "Person", "name": "Raksha Nagaraj"},
        {"@type": "Person", "name": "Sumeet Pai"},
    ]
    assert event["image"].startswith("https://firebasestorage.googleapis.com/")
    assert event["maximumAttendeeCapacity"] == "50"
    assert event["isAccessibleForFree"] is True
    assert event["description"].startswith("What does Bengaluru have to do with quantum physics?")


def test_offsite_programme(monkeypatch):
    event = upcoming(monkeypatch)["Exploring the Molecular World"]
    assert event["location"]["name"] == "National Centre for Biological Sciences (NCBS)"
    assert event["location"]["address"] == "Bangalore"
    assert "image" not in event


def test_programme_without_known_experts(monkeypatch):
    freeze(monkeypatch, 2026, 10, 5)
    [event] = [e for e in filter_data(load("programmes").values(), {}) if e["name"].startswith("D.D.")]
    assert "performer" not in event


def test_main_fetches_season_db(monkeypatch, tmp_path):
    freeze(monkeypatch, 2026, 10, 20)
    urls = []

    def get(url):
        urls.append(url)
        data = load("programmes" if url.endswith("/programmes.json") else "experts")
        return SimpleNamespace(json=lambda: data)

    monkeypatch.setattr(scigallery.requests, "get", get)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    scigallery.main()
    events = json.loads((tmp_path / "out" / "scigalleryblr.json").read_text())
    assert [e["name"] for e in events] == ["The Bengaluru Uncertainty Principle", "Exploring the Molecular World"]
    assert urls == [f"{scigallery.SEASON_DB_HOST}/quantum/en/programmes.json", f"{scigallery.SEASON_DB_HOST}/quantum/en/experts.json"]
