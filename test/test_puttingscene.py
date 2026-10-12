import json
from pathlib import Path

from src.sources import puttingscene
from src.sources.puttingscene import make_events, make_offers


def tier(**kw):
    return {"name": "Regular", "price": {"amount_in_minor_units": 99900}, **kw}


def test_open_tier_counts_seats():
    [offer] = make_offers({"ticket_tiers": [tier(is_sold_out=False, available_capacity=6)]})
    assert offer["availability"] == "https://schema.org/InStock"
    assert offer["remainingAttendeeCapacity"] == 6


def test_closed_tier_drops_unsold_seats():
    [offer] = make_offers({"ticket_tiers": [tier(is_sold_out=True, available_capacity=2)]})
    assert offer["availability"] == "https://schema.org/SoldOut"
    assert "remainingAttendeeCapacity" not in offer


def test_empty_tier_is_sold_out():
    [offer] = make_offers({"ticket_tiers": [tier(available_capacity=0)]})
    assert offer["availability"] == "https://schema.org/SoldOut"
    assert "remainingAttendeeCapacity" not in offer


def test_slot_capacity_is_the_total():
    event = {"id": "E1", "title": "Workshop", "is_paid": True, "slots": [
        {"start_at": "2026-10-10T18:00:00+05:30", "max_attendees": 6, "ticket_tiers": [tier(available_capacity=6)]},
        {"start_at": "2026-10-17T18:00:00+05:30", "ticket_tiers": [tier(available_capacity=6)]},
    ]}
    first, second = make_events(event)
    assert first["maximumAttendeeCapacity"] == 6
    assert "maximumAttendeeCapacity" not in second


FIXTURES = Path(__file__).parent / "fixtures" / "puttingscene"
PLACE = ("Maraa, 2nd Cross, New Thippasandra, Bengaluru", 12.97, 77.65)


def detail(event_id):
    return json.loads((FIXTURES / f"{event_id}.json").read_text())


class FakeResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.data = data

    def json(self):
        return self.data


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append((url, dict(params or {})))
        key = url + ("?" + params["cursor"] if params and "cursor" in params else "")
        return self.pages.get(key) or FakeResponse(404)


def serve(monkeypatch, pages):
    fetcher = FakeFetcher(pages)
    monkeypatch.setattr(puttingscene, "fetcher", fetcher)
    monkeypatch.setattr(puttingscene, "resolve", lambda url: PLACE)
    return fetcher


def test_paid_event_skips_past_slots(monkeypatch):
    monkeypatch.setattr(puttingscene, "resolve", lambda url: None)
    [event] = make_events(detail("EPL7R5"))
    assert event["name"] == "Weekend Games with ReRoll"
    assert event["url"] == "https://puttingscene.com/events/EPL7R5"
    assert event["startDate"] == "2026-10-03T18:00:00+05:30"
    assert event["endDate"] == "2026-10-03T23:00:00+05:30"
    assert event["maximumAttendeeCapacity"] == 30
    assert event["organizer"] == {"@type": "Organization", "name": "Underline Center"}
    assert event["location"]["address"].endswith(", Bangalore")
    assert "geo" not in event["location"]
    [offer] = event["offers"]
    assert offer["price"] == "399.00"
    assert offer["remainingAttendeeCapacity"] == 28


def test_free_external_event(monkeypatch):
    monkeypatch.setattr(puttingscene, "resolve", lambda url: PLACE)
    [event] = make_events(detail("AJYTK5"))
    assert event["isAccessibleForFree"] is True
    assert "offers" not in event
    assert "maximumAttendeeCapacity" not in event
    assert event["sameAs"] == "https://www.instagram.com/p/Dd5l4KtGZEx?img_index=2"
    assert event["image"] == "https://cdn.puttingscene.com/base/image/_HBWMlW9SaeIV7HVVYLh0w.jpg"
    assert event["description"].startswith("Young poets read verse of resistance")
    assert event["location"] == {
        "name": "Maraa Collective, New Thippasandra",
        "address": PLACE[0],
        "url": "https://maps.app.goo.gl/X9vUqYCuv9BwUjSW8",
        "geo": {"@type": "GeoCoordinates", "latitude": 12.97, "longitude": 77.65},
    }


def test_paid_event_without_tiers_uses_starting_price(monkeypatch):
    monkeypatch.setattr(puttingscene, "resolve", lambda url: None)
    [event] = make_events(detail("C5EP3P"))
    assert event["offers"] == [{"@type": "Offer", "price": "400.00", "priceCurrency": "INR"}]
    assert "isAccessibleForFree" not in event


def test_test_and_untitled_events_are_dropped():
    assert make_events(dict(detail("C5EP3P"), title="Test event please ignore")) == []
    assert make_events(dict(detail("C5EP3P"), title=None)) == []


def test_fetch_follows_cursor(monkeypatch):
    listing = json.loads((FIXTURES / "list.json").read_text())
    first = dict(listing, data=listing["data"][:2], page={"has_more": True, "next_cursor": "c2"})
    second = dict(listing, data=listing["data"][2:])
    api = puttingscene.API_BASE
    fetcher = serve(monkeypatch, {api: FakeResponse(200, first), f"{api}?c2": FakeResponse(200, second)})
    assert [e["id"] for e in puttingscene.fetch_event_list()] == ["AJYTK5", "EPL7R5", "C5EP3P"]
    assert [params for _, params in fetcher.calls] == [{"per_page": 50}, {"per_page": 50, "cursor": "c2"}]


def test_fetch_list_failure_is_empty(monkeypatch):
    serve(monkeypatch, {})
    assert puttingscene.fetch_event_list() == []
    assert puttingscene.fetch_event_details("EPL7R5") is None


def test_fetch_putting_scenes(monkeypatch):
    api = puttingscene.API_BASE
    listing = json.loads((FIXTURES / "list.json").read_text())
    listing["data"].append(dict(listing["data"][0], id="GONE", is_in_past=True))
    pages = {api: FakeResponse(200, listing)}
    pages |= {f"{api}/{i}": FakeResponse(200, detail(i)) for i in ("EPL7R5", "C5EP3P")}
    serve(monkeypatch, pages)
    events = puttingscene.fetch_putting_scenes()
    assert [e["url"].rsplit("/", 1)[1] for e in events] == ["EPL7R5", "C5EP3P"]
