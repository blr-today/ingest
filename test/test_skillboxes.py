import json
from pathlib import Path

import pytest

from src.sources import skillboxes

FIXTURES = Path(__file__).parent / "fixtures" / "skillboxes"
API = "https://www.skillboxes.com/servers/v3/api/event-new/"


class FakeResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.data = data

    def json(self):
        if isinstance(self.data, Exception):
            raise self.data
        return self.data


class FakeFetcher:
    def __init__(self, details=None, tickets=None, pages=None):
        self.details = details or {}
        self.tickets = tickets or {}
        self.pages = pages or []
        self.calls = []

    def post(self, url, json=None, headers=None, cache=True):
        self.calls.append((url.removeprefix(API), json, cache))
        if url.endswith("/get-event"):
            page = json["page"] - 1
            return FakeResponse(200, self.pages[page]) if page < len(self.pages) else FakeResponse(503)
        store = self.details if url.endswith("/event-details") else self.tickets
        return store.get(json["slug"]) or FakeResponse(404, {"success": False})


def details():
    return {e["slug"]: e for e in json.loads((FIXTURES / "details.json").read_text())}


def listing(*slugs, more=False):
    page = json.loads((FIXTURES / "list-empty.json").read_text())
    return dict(page, items=[{"slug": s} for s in slugs], total=len(slugs), next=more)


def test_get_events_follows_next_page(monkeypatch):
    fetcher = FakeFetcher(pages=[listing("shimza", more=True), listing("sunday-sundowner-3")])
    monkeypatch.setattr(skillboxes, "fetcher", fetcher)
    assert list(skillboxes.get_events(9)) == ["shimza", "sunday-sundowner-3"]
    assert [(c[1]["page"], c[1]["city"], c[2]) for c in fetcher.calls] == [(1, 9, False), (2, 9, False)]


def test_empty_city(monkeypatch):
    monkeypatch.setattr(skillboxes, "fetcher", FakeFetcher(pages=[json.loads((FIXTURES / "list-empty.json").read_text())]))
    assert list(skillboxes.get_events(9)) == []


def test_failed_listing_raises(monkeypatch):
    monkeypatch.setattr(skillboxes, "fetcher", FakeFetcher())
    with pytest.raises(RuntimeError, match="HTTP 503"):
        list(skillboxes.get_events(9))


def test_event_details(monkeypatch):
    shimza = details()["shimza"]
    monkeypatch.setattr(skillboxes, "fetcher", FakeFetcher(details={"shimza": FakeResponse(200, {"data": shimza})}))
    assert skillboxes.get_event_details("shimza") == shimza
    assert skillboxes.get_event_details("gone") is None


def test_event_tickets(monkeypatch):
    tickets = details()["shimza"]["tickets"]
    monkeypatch.setattr(skillboxes, "fetcher", FakeFetcher(tickets={
        "shimza": FakeResponse(200, {"success": True, "data": tickets}),
        "huge": FakeResponse(200, ValueError("got more than 100 headers")),
        "broken": FakeResponse(200, ValueError("bad json")),
    }))
    assert skillboxes.get_event_tickets("shimza") == tickets
    assert skillboxes.get_event_tickets("closed") == []
    assert skillboxes.get_event_tickets("huge") == []
    assert skillboxes.get_event_tickets("broken") == []


def test_fetch_keeps_city_events_with_tickets(monkeypatch):
    events = details()
    other = dict(events["sunday-sundowner-3"], city_id="3")
    fetcher = FakeFetcher(
        pages=[listing("shimza", "sunday-sundowner-3", "gone")],
        details={"shimza": FakeResponse(200, {"data": events["shimza"]}), "sunday-sundowner-3": FakeResponse(200, {"data": other})},
        tickets={"shimza": FakeResponse(200, {"success": True, "data": events["shimza"]["tickets"]})},
    )
    monkeypatch.setattr(skillboxes, "fetcher", fetcher)
    [event] = skillboxes.fetch_events(["9"])
    assert event == events["shimza"]


def test_fetch_debug_limit(monkeypatch):
    events = details()
    fetcher = FakeFetcher(
        pages=[listing("shimza", "sunday-sundowner-3")],
        details={slug: FakeResponse(200, {"data": e}) for slug, e in events.items()},
    )
    monkeypatch.setattr(skillboxes, "fetcher", fetcher)
    [event] = skillboxes.fetch_events(["9"], debug_limit=1)
    assert event["slug"] == "shimza"
    assert event["tickets"] == []


def test_events_transform_both_cities(monkeypatch):
    events = details()
    fetcher = FakeFetcher(
        pages=[listing("shimza")],
        details={"shimza": FakeResponse(200, {"data": events["shimza"]})},
        tickets={"shimza": FakeResponse(200, {"success": True, "data": events["shimza"]["tickets"]})},
    )
    monkeypatch.setattr(skillboxes, "fetcher", fetcher)
    monkeypatch.setattr(skillboxes, "transform", lambda stem, raw: [{"stem": stem, "raw": json.loads(raw)}])
    assert skillboxes.events() == [{"stem": "skillboxes", "raw": [events["shimza"]]}]
    cities = [body["city"] for url, body, _ in fetcher.calls if url == "get-event"]
    assert cities == [9, 1105542]
