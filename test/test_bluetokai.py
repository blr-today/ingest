import json
from datetime import datetime
from pathlib import Path

import pytest

import bluetokai

LISTING = Path(__file__).parent / "fixtures" / "bluetokai" / "coffee-workshop-events.html"
BODY = "<p>Brew better at home.</p><p>Time: 11 AM - 1 PM</p><p>Venue: Blue Tokai Coffee Roasters, Koramangala, Bengaluru</p>"


def product(body=BODY, variants=None):
    return {"product": {
        "handle": "pour-over-workshop",
        "title": "Pour Over Workshop",
        "body_html": body,
        "image": {"src": "https://cdn.shopify.com/pour-over.jpg"},
        "variants": variants or [
            {"title": "Mumbai - 18th October 2026", "price": "850.00"},
            {"title": "Bengaluru - 18th October 2026", "price": "849.50"},
        ],
    }}


class FakeSession:
    def __init__(self, text="", data=None):
        self.text, self.data, self.urls = text, data, []

    def get(self, url, headers=None):
        self.urls.append(url)
        return self

    def json(self):
        return self.data


def test_current_listing_has_no_bengaluru_events():
    assert bluetokai.parse_html(LISTING.read_text()) == []


def test_listing_links_from_bengaluru_blocks():
    html = (
        '<div class="eventwrapperdiv" location="Bengaluru"><a href="/products/pour-over#x">Pour</a></div>'
        '<div class="eventwrapperdiv" location="Mumbai"><a href="/products/latte-art">Latte</a></div>'
        '<div class="eventwrapperdiv" location="Bangalore"><a href="/products/cupping">Cup</a></div>'
    )
    assert bluetokai.parse_html(html) == ["/products/pour-over#x", "/products/cupping"]


def test_fetchers_use_cached_session(monkeypatch):
    session = FakeSession(text=LISTING.read_text(), data=product())
    monkeypatch.setattr(bluetokai, "get_cached_session", lambda: session)
    assert "events-page-container" in bluetokai.fetch_html()
    assert bluetokai.fetch_product_json("pour-over")["product"]["handle"] == "pour-over-workshop"
    assert session.urls[-1] == "https://bluetokaicoffee.com/products/pour-over.json"


def test_bengaluru_variant_and_date():
    variant, date = bluetokai.find_bengaluru_variant(product())
    assert variant["price"] == "849.50"
    assert (date.month, date.day) == (10, 18)
    assert bluetokai.find_bengaluru_variant(product(variants=[{"title": "Delhi - 1 Nov", "price": "1"}])) == (None, None)


def test_timing_ranges():
    assert bluetokai.extract_timing("<p>12 PM - 2 PM</p>") == (12, 14)
    assert bluetokai.extract_timing("<p>11 PM - 4 PM</p>") == (11, 16)
    assert bluetokai.extract_timing("<p>Starts at 5 PM</p>") == (17, 19)
    assert bluetokai.extract_timing("<p>Evening</p>") is None


def test_location_from_body():
    assert bluetokai.guess_location(BODY)[1] == "Blue Tokai Coffee Roasters Koramangala"
    assert bluetokai.guess_location("<p>Blue Tokai Coffee Roasters, HSR Layout</p>")[1:] == (
        "Blue Tokai Coffee Roasters HSR Layout", 12.91279211, 77.64475762)
    assert bluetokai.guess_location("<p>Somewhere in Pune</p>") is None


def test_event_object():
    variant, date = bluetokai.find_bengaluru_variant(product())
    event = bluetokai.generate_event_object(product(), variant, datetime(2026, 10, 18), 11, 13)
    assert event["url"] == "https://bluetokaicoffee.com/products/pour-over-workshop"
    assert event["startDate"] == "2026-10-18T11:00:00+05:30"
    assert event["endDate"] == "2026-10-18T13:00:00+05:30"
    assert event["offers"]["price"] == "850"
    assert event["location"]["address"] == "Blue Tokai Coffee Roasters Koramangala Bengaluru"
    assert event["description"].startswith("Brew better at home.")


def test_event_without_blr_location(capsys):
    variant, _ = bluetokai.find_bengaluru_variant(product())
    assert bluetokai.generate_event_object(product(body="<p>Pune</p>"), variant, datetime(2026, 10, 18), 11, 13) is None
    assert "Could not find a location" in capsys.readouterr().out


def test_main_writes_events(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    monkeypatch.setattr(bluetokai, "fetch_html", lambda: '<div location="Bengaluru"><a href="/products/pour-over#a">x</a></div>')
    monkeypatch.setattr(bluetokai, "fetch_product_json", lambda slug: product())
    bluetokai.main()
    [event] = json.loads((tmp_path / "out" / "bluetokai.json").read_text())
    assert event["name"] == "Pour Over Workshop"
    assert event["startDate"][4:] == "-10-18T11:00:00+05:30"
