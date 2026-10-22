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


def test_lookup_ignores_city_and_area_suffixes():
    assert lookup("HEYOU | The Oberoi, MG Road")["name"] == "Heyou"
    assert lookup("Courtyard: Bengaluru.")
    assert lookup("Courtyard, Bangalore")


def test_lookup_matches_listing_spellings():
    assert (
        lookup("Fabrizo - Creative Art Craft & Bake Lounge")["name"]
        == "Fabrizo, BTM Layout"
    )
    assert lookup("Shoonya - Centre for Art and Somatic Practices")
    assert lookup("Foodstories Bangalore")
    assert lookup("Sabha")


def test_one_word_names_need_exact_match():
    assert lookup("Courtyard")
    assert lookup("Courtyard by Marriott, Hebbal") is None


def test_fills_only_missing_geo():
    event = {"location": {"name": "Cubbon Park"}}
    assert Venues.process("u", event)["location"]["geo"]["latitude"] == 12.97425
    kept = {"location": {"name": "Cubbon Park", "geo": {"latitude": 1, "longitude": 2}}}
    assert Venues.process("u", kept)["location"]["geo"]["latitude"] == 1


def test_names_unnamed_places_at_a_known_venue():
    near = {
        "location": {"name": "", "geo": {"latitude": 12.99679, "longitude": 77.61988}}
    }
    assert Venues.process("u", near)["location"]["name"] == "Angala, Cox Town"
    far = {
        "location": {"name": None, "geo": {"latitude": 12.99778, "longitude": 77.61987}}
    }
    assert Venues.process("u", far)["location"]["name"] is None
    named = {
        "location": {
            "name": "Host",
            "geo": {"latitude": 12.99679, "longitude": 77.61988},
        }
    }
    assert Venues.process("u", named)["location"]["name"] == "Host"


def test_snaps_nearby_pins_to_the_venue():
    for lat, lng in [(12.9672214, 77.6366982), (12.9672315, 77.6367239)]:
        event = {"location": {"name": "Underline Center", "geo": {"latitude": lat, "longitude": lng}}}
        geo = Venues.process("u", event)["location"]["geo"]
        assert (geo["latitude"], geo["longitude"]) == (12.96725, 77.63674)
    far = {"location": {"name": "Underline Center", "geo": {"latitude": 12.97, "longitude": 77.64}}}
    assert Venues.process("u", far)["location"]["geo"]["latitude"] == 12.97


def test_drops_the_city_from_place_names():
    names = {
        "BudBee Restobar 104: Bengaluru": "BudBee Restobar 104",
        "Hobby Ghar: Seshadripuram, Bengaluru.": "Hobby Ghar: Seshadripuram",
        "The Humming Tree Bar and Bistro | Indiranagar, Bangalore": "The Humming Tree Bar and Bistro | Indiranagar",
        "Fortius Origin, Koramangala, Bengaluru, Karnataka, India": "Fortius Origin, Koramangala",
        "Science Gallery Bengaluru": "Science Gallery Bengaluru",
        "Bengaluru": "Bengaluru",
    }
    for before, after in names.items():
        event = {"location": {"name": before, "address": f"{before}, India"}}
        place = Venues.process("u", event)["location"]
        assert place["name"] == after
        assert place["address"] == f"{before}, India"
