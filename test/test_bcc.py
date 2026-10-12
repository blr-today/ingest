import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import requests

from bcc import API_URL, fetch_events, make_event, to_ist

DATA = json.loads((Path(__file__).parent / "fixtures/bcc/events.json").read_text())


class PagedSession:
    def __init__(self, page_size):
        self.page_size = page_size
        self.pages = []

    def get(self, url, params, timeout):
        assert url == API_URL
        self.pages.append(params["page"])
        start = (params["page"] - 1) * self.page_size
        data = dict(DATA, page_size=self.page_size, events=DATA["events"][start : start + self.page_size])
        return SimpleNamespace(json=lambda: data)


def test_to_ist():
    assert to_ist("2026-10-31T04:30:00Z") == "2026-10-31T10:00:00+05:30"


def test_fetch_events_single_page():
    session = PagedSession(20)
    assert len(list(fetch_events(session))) == 3
    assert session.pages == [1]


def test_fetch_events_follows_pages():
    session = PagedSession(2)
    slugs = [e["slug"] for e in fetch_events(session)]
    assert slugs == [e["slug"] for e in DATA["events"]]
    assert session.pages == [1, 2]


def test_make_event():
    event = make_event(DATA["events"][0])
    assert event["name"] == "Chess Connect - Blitz - Bangalore Chess Club"
    assert event["startDate"] == "2026-10-31T10:00:00+05:30"
    assert event["endDate"] == "2026-10-31T13:00:00+05:30"
    assert event["url"] == "https://bangalorechessclub.in/events/chess-connect-blitz-2026-10-31"
    assert event["location"]["name"] == "Blue Tokai"
    assert event["location"]["address"].startswith("WTC Annexe, Dr Rajkumar Road")
    assert event["location"]["hasMap"] == "https://maps.app.goo.gl/vfh23ZchWF86wDsHA"
    assert event["isAccessibleForFree"] is False
    assert event["offers"][0]["price"] == "350"
    assert event["offers"][0]["availability"] == "https://schema.org/InStock"
    assert "image" not in event


def test_make_event_sold_out_free_without_venue():
    e = dict(DATA["events"][0], venue=None, price_inr=None, is_available=False)
    event = make_event(e)
    assert event["location"]["address"] == "Bengaluru, India"
    assert "hasMap" not in event["location"]
    assert event["isAccessibleForFree"] is True
    assert event["offers"][0]["price"] == "0"
    assert event["offers"][0]["availability"] == "https://schema.org/SoldOut"


def test_image_paths():
    e = DATA["events"][0]
    assert make_event(dict(e, image_path="/uploads/a.jpg"))["image"] == "https://bangalorechessclub.in/uploads/a.jpg"
    assert make_event(dict(e, image_path="https://cdn.example/a.jpg"))["image"] == "https://cdn.example/a.jpg"


def test_main_skips_past_events(monkeypatch, tmp_path):
    past = dict(DATA["events"][1], is_past=True)
    data = dict(DATA, events=[DATA["events"][0], past])
    session = SimpleNamespace(get=lambda url, params, timeout: SimpleNamespace(json=lambda: data))
    monkeypatch.setattr(requests, "Session", lambda: session)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    runpy.run_module("bcc", run_name="__main__")
    [event] = json.loads((tmp_path / "out/bcc.json").read_text())
    assert event["name"] == "Chess Connect - Blitz - Bangalore Chess Club"
