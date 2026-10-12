import json
from pathlib import Path

import indiarunning
from indiarunning import convert_to_schema_org, fetch_events, html_to_text, parse_datetime

FIXTURE = Path(__file__).parent / "fixtures" / "indiarunning" / "events.json"


def api_events():
    return json.loads(FIXTURE.read_text())["events"]


class FakeResponse:
    def __init__(self, status_code, data=None):
        self.status_code = status_code
        self.data = data

    def json(self):
        return self.data


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, json=None):
        self.calls.append((url, json))
        return self.response


def test_parse_datetime_converts_utc_to_ist():
    assert parse_datetime("2026-02-15T01:00:00.000Z").isoformat() == "2026-02-15T06:30:00+05:30"
    assert parse_datetime("") is None
    assert parse_datetime(None) is None


def test_html_to_text_strips_markup():
    assert html_to_text("<p>One</p><p>Two</p>") == "One\nTwo"
    assert html_to_text("") == ""
    assert html_to_text(None) == ""


def test_converts_api_event():
    event = convert_to_schema_org(api_events()[0])
    assert event["@type"] == "SportsEvent"
    assert event["name"] == "Wesness Move with Glow Bengaluru"
    assert event["url"] == "https://indiarunning.com/events/wesnessmovewiththeglow-18426"
    assert event["startDate"] == "2026-02-15T06:30:00+05:30"
    assert event["endDate"] == "2026-02-15T08:30:00+05:30"
    assert event["sport"] == "Running"
    assert event["image"].endswith("/banner1770190681945")
    assert event["description"].startswith("This 4.5K community run is all about moving together.")
    assert "<" not in event["description"]
    location = event["location"]
    assert location["name"] == "Westside - New Commercial Street"
    assert location["address"]["postalCode"] == "560042"
    assert location["address"]["addressLocality"] == "Bengaluru"
    assert location["geo"] == {"@type": "GeoCoordinates", "latitude": 12.9824731, "longitude": 77.6107907}
    assert event["offers"] == [{
        "@type": "Offer",
        "name": "4.5K",
        "price": "499",
        "priceCurrency": "INR",
        "availability": "http://schema.org/InStock",
    }]
    assert "organizer" not in event


def test_one_offer_per_category():
    event = convert_to_schema_org(api_events()[2])
    assert [o["name"] for o in event["offers"]] == ["3K", "5k", "10k"]
    assert {o["price"] for o in event["offers"]} == {"650"}


def test_sold_out_category():
    raw = api_events()[0]
    raw["categories"][0]["status"] = "sold_out"
    raw["categories"].append({"category": "1K", "status": "closed"})
    sold_out, unknown = convert_to_schema_org(raw)["offers"]
    assert sold_out["availability"] == "http://schema.org/SoldOut"
    assert "availability" not in unknown


def test_price_without_categories():
    raw = api_events()[1]
    raw["categories"] = []
    assert convert_to_schema_org(raw)["offers"] == [{"@type": "Offer", "price": "299", "priceCurrency": "INR"}]
    raw["price"] = None
    assert "offers" not in convert_to_schema_org(raw)


def test_free_category_has_zero_price():
    raw = api_events()[1]
    raw["price"] = 0
    assert {o["price"] for o in convert_to_schema_org(raw)["offers"]} == {"0"}


def test_sparse_event_falls_back():
    raw = api_events()[0]
    raw.update(slug="", imageUrls=[], sportsType=[], aboutRace=[], orgName="Glow Gang")
    raw["eventDate"].pop("end")
    raw["locationInfo"].pop("latitude")
    event = convert_to_schema_org(raw)
    assert event["url"] == ""
    assert event["image"] == ""
    assert event["sport"] == "Running"
    assert event["description"] == ""
    assert event["endDate"] == event["startDate"]
    assert "geo" not in event["location"]
    assert event["organizer"] == {"@type": "Organization", "name": "Glow Gang"}


def test_skips_events_without_title_or_start():
    raw = api_events()[0]
    assert convert_to_schema_org(dict(raw, title="  ")) is None
    assert convert_to_schema_org(dict(raw, eventDate={})) is None


def test_fetch_events_posts_city(monkeypatch):
    session = FakeSession(FakeResponse(201, json.loads(FIXTURE.read_text())))
    monkeypatch.setattr(indiarunning, "session", session)
    assert len(fetch_events()) == 3
    assert session.calls == [(indiarunning.API_URL, {"type": "event_city", "name": "Bengaluru"})]


def test_fetch_events_failure_is_empty(monkeypatch):
    monkeypatch.setattr(indiarunning, "session", FakeSession(FakeResponse(500)))
    assert fetch_events() == []


def test_main_writes_sorted_events(monkeypatch, tmp_path):
    events = api_events()
    events.insert(0, dict(events[0], title=""))
    monkeypatch.setattr(indiarunning, "fetch_events", lambda: list(reversed(events)))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    indiarunning.main()
    out = json.loads((tmp_path / "out" / "indiarunning.json").read_text())
    assert [e["name"] for e in out] == ["Wesness Move with Glow Bengaluru", "Nivia Sports x PaceX", "Kanyathon 2026"]
