import json
from pathlib import Path

import pytest

from src.sources import urbanaut
FIXTURES = Path(__file__).parent / "fixtures" / "urbanaut"


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def json(self):
        return self.data


class FakeSession:
    def __init__(self):
        self.calls = []
        self.overrides = {}

    def post(self, url, headers=None, json=None):
        self.calls.append((url, headers, json))
        return FakeResponse(load("search"))

    def get(self, url):
        self.calls.append((url,))
        slug = url.split("/data/")[1].split("/")[0]
        return FakeResponse(self.overrides.get(slug) or load(slug))


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


@pytest.fixture
def session(monkeypatch):
    fake = FakeSession()
    monkeypatch.setattr(urbanaut, "session", fake)
    return fake


def spots():
    return {h["document"]["slug"]: h["document"] for h in load("search")["results"][0]["hits"]}


def test_search_filters_bengaluru_events(session):
    result = urbanaut.scrape_urbanaut()
    assert len(result["hits"]) == 4
    url, headers, body = session.calls[0]
    assert url == urbanaut.SEARCH_URL
    assert headers == {"x-typesense-api-key": urbanaut.TYPESENSE_API_KEY}
    assert "city:=Bengaluru && category_data.name:=[Events]" in body["searches"][0]["filter_by"]


def test_slots_are_flattened_across_dates(session):
    slots = urbanaut.get_slots("design-thinking-for-teens")
    assert [s["start"] for s in slots] == ["2026-10-11 11:00:00", "2026-10-18 11:00:00"]
    assert "/data/design-thinking-for-teens/?after=" in session.calls[0][0]


def test_age_range_from_audience_tags():
    found = spots()
    assert urbanaut.get_age_range(found["we-are-okay-bangalore"]) == "21+"
    assert urbanaut.get_age_range(found["design-thinking-for-teens"]) == "2-"
    assert urbanaut.get_age_range(found["dialogues-with-books"]) == "12+"
    assert urbanaut.get_age_range({"who_is_it_for_tag": [{"path": "who_is_it_tags/for_couples.png"}]}) == "16+"
    assert urbanaut.get_age_range({"who_is_it_for_tag": [{"path": "who_is_it_tags/for_all_ages.png"}]}) == "5+"


def test_event_type_from_name_and_genre():
    found = spots()
    assert urbanaut.get_event_type(found["kalighat-painting-workshop"]) == "EducationEvent"
    assert urbanaut.get_event_type(found["we-are-okay-bangalore"]) == "Event"
    assert urbanaut.get_event_type({"name": "Film Screening", "genre_tag": []}) == "ScreeningEvent"
    assert urbanaut.get_event_type({"name": "Dinner", "genre_tag": [{"path": "genretags/food.png"}]}) == "FoodEvent"


def test_keywords_tag_courtyard_events():
    assert urbanaut.get_keywords(spots()["kalighat-painting-workshop"]) == ["Leisure", "Workshop", "URBANAUT"]
    assert urbanaut.get_keywords({"account_slug": "courtyard"}) == ["COURTYARD", "URBANAUT"]


def test_single_slot_event(session):
    [event] = urbanaut.make_event(spots()["we-are-okay-bangalore"])
    assert event["name"] == "We Are Okay! Tour | Begum Live in Bangalore"
    assert event["url"] == "https://urbanaut.app/spot/we-are-okay-bangalore"
    assert event["startDate"] == "2026-10-16T21:00:00+05:30"
    assert event["endDate"] == "2026-10-16T23:59:00+05:30"
    assert event["maximumAttendeeCapacity"] == 500
    assert event["remainingAttendeeCapacity"] == 160
    assert event["typicalAgeRange"] == "21+"
    assert event["offers"]["price"] == 699.0
    assert event["offers"]["priceCurrency"] == "INR"
    assert event["image"][0].startswith(urbanaut.BASE_IMAGE_URL + "/images/")
    assert event["organizer"]["url"] == "https://urbanaut.app/partner/nikamma"
    assert "<" not in event["description"]
    location = event["location"]
    assert location["name"] is None
    assert location["geo"] == {"@type": "GeoCoordinates", "latitude": 12.9711178, "longitude": 77.6410673}
    assert location["url"].endswith("query_place_id=ChIJVVVFg3sWrjsRDaEdPFzPJvc")


def test_multiple_slots_get_fragment_urls(session):
    events = list(urbanaut.make_event(spots()["design-thinking-for-teens"]))
    assert [e["url"] for e in events] == [
        "https://urbanaut.app/spot/design-thinking-for-teens#2026-10-11T1100",
        "https://urbanaut.app/spot/design-thinking-for-teens#2026-10-18T1100",
    ]


def test_sold_out_slots_are_skipped(session):
    slots = load("design-thinking-for-teens")
    slots["dates"][0]["slots"][0]["available"] = 0
    session.overrides["design-thinking-for-teens"] = slots
    [event] = urbanaut.make_event(spots()["design-thinking-for-teens"])
    assert event["url"] == "https://urbanaut.app/spot/design-thinking-for-teens"
    assert event["startDate"] == "2026-10-18T11:00:00+05:30"


def test_host_venue_and_missing_place(session):
    spot = dict(spots()["kalighat-painting-workshop"], account_slug="courtyard")
    [event] = urbanaut.make_event(spot)
    assert event["location"]["name"] == "HUES BY SINDHOOR"
    assert "url" not in event["location"]
    assert event["keywords"][-2:] == ["COURTYARD", "URBANAUT"]
