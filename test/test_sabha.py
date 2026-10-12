import json
import re
from datetime import date
from pathlib import Path

import pytest

import sabha

FIXTURES = Path(__file__).parent / "fixtures" / "sabha"


class FakeResponse:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


class FakeSession:
    def get(self, url):
        name = "events" if url == sabha.EVENTS_URL else url.rsplit("/", 1)[-1]
        path = FIXTURES / f"{name}.html"
        return FakeResponse(path.read_text() if path.exists() else "", 200 if path.exists() else 404)


class Today(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 1)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(sabha, "date", Today)
    monkeypatch.setattr(sabha, "get_cached_session", FakeSession)


def raw_events():
    html = (FIXTURES / "events.html").read_text()
    data = json.loads(re.search(r'id="wix-warmup-data">(.*?)</script>', html, re.S).group(1))
    widgets = data["appsWarmupData"]["140603ad-af8d-84a5-2c80-a0f60cb47351"].values()
    return {e["slug"]: e for w in widgets for e in w.get("events", {}).get("events", [])}


def test_long_description_joins_paragraphs():
    text = sabha.fetch_event_detail("flying-tigers", FakeSession())
    assert text.splitlines() == [
        "Flying Tigers",
        "A film by Madhusree Dutta",
        "105 minutes | 2026 | Bengali, English, Mandarin, German with English subtitles",
    ]


def test_long_description_bullets_list_items():
    lines = sabha.fetch_event_detail("sound-of-the-goddess", FakeSession()).splitlines()
    assert lines[:2] == ["What to Expect", "The afternoon will seamlessly weave together:"]
    assert len([l for l in lines if l.startswith("- ")]) >= 2
    assert lines[-1] == "No prior experience with chanting or meditation is necessary. All are welcome."


def test_missing_detail_page_has_no_description():
    assert sabha.fetch_event_detail("no-such-event", FakeSession()) is None


def test_parse_datetime_converts_to_ist():
    assert sabha.parse_datetime("2026-11-11T13:00:00.000Z") == "2026-11-11T18:30:00+05:30"


def test_ticketed_event_gets_offer_and_description():
    [event] = sabha.transform_event(raw_events()["flying-tigers"], FakeSession())
    assert event["name"] == "Flying Tigers - Vikalp Bengaluru Presents"
    assert event["url"] == "https://www.sabhablr.in/event-details/flying-tigers"
    assert event["startDate"] == "2026-11-11T18:30:00+05:30"
    assert event["endDate"] == "2026-11-11T21:00:00+05:30"
    assert event["offers"] == {"@type": "Offer", "availability": "SoldOut"}
    assert event["description"].startswith("Flying Tigers\nA film by")
    assert event["image"].startswith("https://static.wixstatic.com/media/")
    assert "sameAs" not in event


def test_external_event_links_registration():
    [event] = sabha.transform_event(raw_events()["the-garba-circle-1"], FakeSession())
    assert event["sameAs"] == "https://sortmyscene.com/event/the-garba-circle-oct-15-2026"
    assert "offers" not in event
    assert "description" not in event


def test_multi_day_event_splits_per_day():
    first, second = sabha.transform_event(raw_events()["angels-egg"], FakeSession())
    assert first["name"] == "Angel's Egg - Oct 03"
    assert second["name"] == "Angel's Egg - Oct 04"
    assert first["startDate"] == "2026-10-03T21:30:00+05:30"
    assert first["endDate"] == "2026-10-03T22:40:00+05:30"
    assert second["startDate"] == "2026-10-04T21:30:00+05:30"
    assert first["url"] == "https://www.sabhablr.in/event-details/angels-egg#2026-10-03"
    assert second["url"] == "https://www.sabhablr.in/event-details/angels-egg#2026-10-04"


def test_fetch_events_keeps_every_day_of_multi_day_events():
    names = [e["name"] for e in sabha.fetch_events()]
    assert names.count("Angel's Egg - Oct 03") == 1
    assert names.count("Angel's Egg - Oct 04") == 1


def test_past_event_is_dropped():
    assert sabha.transform_event(raw_events()["maithreem-bhajatha-1"], FakeSession()) is None


def test_event_without_slug_is_dropped():
    event = dict(raw_events()["flying-tigers"], slug="")
    assert sabha.transform_event(event, FakeSession()) is None


def test_fetch_events_dedupes_across_widgets():
    urls = [e["url"].rsplit("/", 1)[-1] for e in sabha.fetch_events()]
    assert urls.count("from-silos-to-systems") == 1
    assert "maithreem-bhajatha-1" not in urls
    assert "young-voices-bhakti-sangeetam" not in urls
    assert {"flying-tigers", "the-garba-circle-1"} <= set(urls)


def test_fetch_events_without_warmup_data(monkeypatch):
    monkeypatch.setattr(FakeSession, "get", lambda self, url: FakeResponse("<html></html>"))
    assert sabha.fetch_events() == []
