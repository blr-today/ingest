import json
from pathlib import Path

from src.processors.geo import GeoProcessor, extract_coords, haversine_distance

ROWS = json.loads(
    (Path(__file__).parent / "fixtures/processors/events.json").read_text()
)


def at(lat, lng, keywords=None):
    event = {
        "location": {"name": "Somewhere", "geo": {"latitude": lat, "longitude": lng}}
    }
    if keywords is not None:
        event["keywords"] = keywords
    return event


def test_haversine_distance():
    assert haversine_distance(12.97, 77.59, 12.97, 77.59) == 0
    # Bangalore to Delhi airport is about 1700km
    assert 1700 < haversine_distance(12.97, 77.59, 28.556144, 77.099962) < 1750


def test_extract_coords():
    assert extract_coords(at("12.9", "77.6")) == (12.9, 77.6)
    assert extract_coords(at("north", "77.6")) == (None, None)
    assert extract_coords(at(None, 77.6)) == (None, None)
    assert extract_coords({"location": "Bangalore"}) == (None, None)
    assert extract_coords({"location": {"geo": "12.9,77.6"}}) == (None, None)
    assert extract_coords({}) == (None, None)


def test_far_events_are_tagged():
    url, event = next(r for r in ROWS if "highape" in r[0])
    event = GeoProcessor.process(url, json.loads(json.dumps(event)))
    assert event["keywords"] == ["HIGHAPE", "NOTINBLR"]
    assert GeoProcessor.process("u", at(13.5, 77.6))["keywords"] == ["NOTINBLR"]
    assert GeoProcessor.process("u", at(13.5, 77.6, {"content": "x"}))["keywords"] == [
        "NOTINBLR"
    ]


def test_tag_is_added_once():
    event = at(28.5, 77.1, ["NOTINBLR", "X"])
    assert GeoProcessor.process("u", event)["keywords"] == ["NOTINBLR", "X"]


def test_nearby_events_are_untouched():
    url, event = next(r for r in ROWS if "district" in r[0])
    assert "keywords" not in GeoProcessor.process("u", at(13.2, 77.6))
    assert GeoProcessor.process(url, dict(event)) == event


def test_zero_coordinates_are_dropped():
    event = GeoProcessor.process("u", at(0, 77.6, ["X"]))
    assert event == {"location": {"name": "Somewhere"}, "keywords": ["X"]}
    assert "geo" not in GeoProcessor.process("u", at("12.9", "0"))["location"]


def test_impossible_coordinates_are_skipped(caplog):
    for lat, lng in ((95, 77.6), (12.9, 400), ("nan", 77.6), ("-Infinity", 77.6)):
        event = at(lat, lng, ["X"])
        assert GeoProcessor.process("https://x.in/e", json.loads(json.dumps(event))) == event
    assert caplog.text.count("GeoProcessor skipped coordinates") == 4
    assert "skipped coordinates 95.0, 77.6 for https://x.in/e" in caplog.text
