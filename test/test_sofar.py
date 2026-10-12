import json
from pathlib import Path

import sofar
from sofar import to_schema_org_music_event

FIXTURE = Path(__file__).parent / "fixtures" / "sofar" / "events.json"


def response():
    return json.loads(FIXTURE.read_text())


def raw_event():
    return response()["data"]["events"]["events"][0]


def test_converts_event():
    event = to_schema_org_music_event(raw_event())
    assert event["url"] == "https://www.sofarsounds.com/events/67871"
    assert event["name"] == "Sofar concert in Bangalore"
    assert event["doorTime"] == "2026-10-24T15:30:00+05:30"
    assert event["startDate"] == "2026-10-24T16:00:00+05:30"
    assert event["endDate"] == "2026-10-24T18:00:00+05:30"
    assert event["location"] == {"@type": "Place", "address": "Bangalore"}
    assert event["remainingAttendeeCapacity"] == 100
    assert event["image"].startswith("https://sofar-sounds-live.imgix.net/")
    assert event["offers"] == {
        "@type": "Offer",
        "price": 904.0,
        "priceCurrency": "INR",
        "availability": "https://schema.org/InStock",
    }


def test_neighbourhood_names_the_event():
    raw = raw_event()
    raw["venue"] = {"neighborhood": {"title": "Indiranagar"}, "venueName": None, "venueCategories": []}
    event = to_schema_org_music_event(raw)
    assert event["name"] == "Sofar concert in Indiranagar"
    assert event["location"]["address"] == "Indiranagar"


def test_unconfirmed_venue_falls_back_to_city():
    raw = dict(raw_event(), venue=None)
    assert to_schema_org_music_event(raw)["name"] == "Sofar concert in Bangalore"


def test_main_writes_events(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(sofar, "make_graphql_request", lambda *args: calls.append(args) or response())
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    sofar.main()
    [event] = json.loads((tmp_path / "out" / "sofar.json").read_text())
    assert event["url"] == "https://www.sofarsounds.com/events/67871"
    assert calls[0][1] == "bangalore"


def test_graphql_request_asks_for_the_city(monkeypatch):
    sent = {}

    class FakeResponse:
        content = FIXTURE.read_bytes()

    def post(url, json=None, impersonate=None):
        sent.update(url=url, body=json, impersonate=impersonate)
        return FakeResponse()

    monkeypatch.setattr(sofar.curl_cffi, "post", post)
    assert sofar.make_graphql_request(sofar.query, "bangalore", sofar.url) == response()
    assert sent["body"]["variables"]["city"] == "bangalore"
    assert sent["impersonate"] == sofar.BROWSER_CODE


def test_theme_and_venue_category_name_the_event():
    raw = raw_event()
    raw["eventThemes"] = [{"title": "Acoustic"}]
    raw["venue"] = {"neighborhood": {"title": "Indiranagar"}, "venueName": None, "venueCategories": [{"name": "Rooftop"}]}
    assert to_schema_org_music_event(raw)["name"] == "Acoustic Sofar concert at a Rooftop in Indiranagar"
    raw["eventThemes"] = []
    raw["venue"]["venueCategories"] = [{"name": "Other"}]
    assert to_schema_org_music_event(raw)["name"] == "Sofar concert in Indiranagar"
