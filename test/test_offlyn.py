import datetime
import json
from pathlib import Path
from types import SimpleNamespace

from src.sources import offlyn

FIXTURES = Path(__file__).parent / "fixtures/offlyn"
LISTING = json.loads((FIXTURES / "page1.json").read_text())
PAGES = {offlyn.PAGE + "diwaliatpraks": (FIXTURES / "diwaliatpraks.html").read_text()}


def serve(monkeypatch, now=(2026, 11, 5)):
    calls = []

    def get(url, params=None, headers=None, timeout=None):
        calls.append(params)
        if url == offlyn.API:
            body = LISTING if params["page"] == 1 else LISTING | {"experiences": []}
            return SimpleNamespace(json=lambda: body, raise_for_status=lambda: None)
        return SimpleNamespace(text=PAGES.get(url, "<html></html>"))

    class Fixed(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(*now, tzinfo=tz)

    monkeypatch.setattr(offlyn, "datetime", SimpleNamespace(datetime=Fixed))
    monkeypatch.setattr(offlyn, "get_cached_session", lambda: SimpleNamespace(get=get))
    return calls


def test_listing_and_page_details(monkeypatch):
    serve(monkeypatch)
    events = {e["url"]: e for e in offlyn.events()}
    assert len(events) == 3
    praks = events["https://offlyn.life/e/diwaliatpraks"]
    assert praks["startDate"] == "2026-11-06T17:00:00+05:30"
    assert praks["endDate"] == "2026-11-08T22:00:00+05:30"
    assert praks["organizer"] == {"@type": "Organization", "name": "Prakriti"}
    assert praks["location"] == {"@type": "Place", "name": "Bellandur, Bengaluru", "address": "Bellandur, Bengaluru"}
    assert praks["description"].startswith("Hi, I’m so glad you stopped by!")
    assert [o["price"] for o in praks["offers"]] == [899, 999]
    assert praks["keywords"] == ["Art & Culture", "Community Meetup", "Social Mixer"]


def test_listing_fills_in_without_a_page(monkeypatch, caplog):
    serve(monkeypatch)
    events = {e["url"]: e for e in offlyn.events()}
    edit = events["https://offlyn.life/e/thediwaliedit"]
    assert edit["location"]["name"] == "Dialogues Cafe Koramangala"
    assert edit["location"]["geo"] == {"@type": "GeoCoordinates", "latitude": 12.9324179, "longitude": 77.631954}
    assert edit["offers"]["price"] == 899
    assert "description" not in edit
    assert events["https://offlyn.life/e/BachpanWaaliDiwali"]["location"]["name"] == "Bengaluru"
    assert "No page details for https://offlyn.life/e/thediwaliedit" in caplog.text


def test_past_events_are_skipped(monkeypatch):
    serve(monkeypatch, now=(2026, 11, 8))
    assert [e["name"] for e in offlyn.events()] == ["Ghar Waali Diwali - by Praks 🪔✨"]


def test_pages_until_total(monkeypatch):
    calls = serve(monkeypatch)
    offlyn.events()
    assert [c["page"] for c in calls if c] == [1]
