from src.processors.venues import Venues, lookup


def test_lookup_matches_variants():
    assert (
        lookup("Wadia Hall, Indian Institute of World Culture")["name"]
        == "Indian Institute of World Culture"
    )
    assert (
        lookup("St. Joseph's Arts And Science College")["name"]
        == "St Joseph's University"
    )
    assert lookup("Alliance Française de Bangalore, Vasanth Nagar")


def test_one_word_names_need_exact_match():
    assert lookup("Courtyard")
    assert lookup("Courtyard by Marriott, Hebbal") is None


def test_fills_only_missing_geo():
    event = {"location": {"name": "Cubbon Park"}}
    assert Venues.process("u", event)["location"]["geo"]["latitude"] == 12.97525
    kept = {"location": {"name": "Cubbon Park", "geo": {"latitude": 1, "longitude": 2}}}
    assert Venues.process("u", kept)["location"]["geo"]["latitude"] == 1
