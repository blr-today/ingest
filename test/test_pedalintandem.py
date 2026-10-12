from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

import pedalintandem

FIXTURES = Path(__file__).parent / "fixtures" / "pedalintandem"
NANDI = "/experiences/cycle-rides-blr/nandi-countryside"


def page(old="", new=""):
    return (FIXTURES / "nandi-countryside.html").read_text().replace(old, new)


class FakeSession:
    pages = {
        "/experiences": (FIXTURES / "experiences.html").read_text(),
        NANDI: page(),
        "/experiences/thePITStop/cycle-school": page("Nandi, Bengaluru", "Coorg"),
        "/experiences/cycle-tours/hampi": page("3-5 hours", "2D/ 1N"),
    }

    def get(self, url):
        return SimpleNamespace(text=self.pages[url.removeprefix(pedalintandem.BASE_URL)])


class FakeClient:
    def __init__(self, **choices):
        self.choices = choices

    def system_one(self, state, questions):
        self.state, self.questions = state, questions
        return SimpleNamespace(
            nouls={"has_end": SimpleNamespace(noul=0.1)},
            choices={k: SimpleNamespace(choice=v, confidence=0.9) for k, v in self.choices.items()},
        )


class Today(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 12)


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    monkeypatch.setattr(pedalintandem, "date", Today)


def soup():
    return BeautifulSoup(page(), "html.parser")


def test_listing_links():
    assert list(pedalintandem.fetch_events_links(FakeSession())) == [
        "/experiences/thePITStop/cycle-school",
        NANDI,
        "/experiences/cycle-tours/hampi",
    ]


def test_fetch_events_keeps_single_day_blr_rides(capsys):
    links = pedalintandem.fetch_events_links(FakeSession())
    [[event, link]] = pedalintandem.fetch_events(links, FakeSession())
    assert link == NANDI
    assert event.select_one("div.location").get_text(strip=True) == "Nandi, Bengaluru"
    out = capsys.readouterr().out
    assert "cycle-school coorg not in BLR" in out
    assert "hampi is 2D/ 1N long" in out


def test_location_falls_back_to_listed_place():
    assert pedalintandem.find_location(soup()) == {"@type": "Place", "address": "nandi, bengaluru"}


def test_shop_location_uses_known_address():
    html = page("Nandi, Bengaluru", "Pedal in Tandem")
    location = pedalintandem.find_location(BeautifulSoup(html, "html.parser"))
    assert location["name"] == "Pedal in Tandem"
    assert "Indiranagar" in location["address"]


def test_duration_in_hours():
    assert pedalintandem.convert_duration_in_hours("3-5 hours") == 5
    assert pedalintandem.convert_duration_in_hours("2 to 3 hrs, with breakfast") == 3
    assert pedalintandem.convert_duration_in_hours("4 hours") == 4
    assert pedalintandem.convert_duration_in_hours("Half day") == 0


def test_offers_split_rides_from_rentals():
    offers = pedalintandem.get_offers(soup().select_one("div.cart-details"))
    assert [(o["name"].strip(), o["price"]) for o in offers] == [
        ("l1 - beginner- 30 km (with b'fast)", "3150"),
        ("l2 - moderate - 50 km (with b'fast)", "3420"),
    ]
    assert [(a["name"], a["price"]) for a in offers[0]["addOn"]] == [
        ("rental bike (with transport)", "900"),
        ("transport my bicycle", "400"),
    ]


def test_location_without_any_match_has_no_address():
    assert pedalintandem.find_location(BeautifulSoup("<div></div>", "html.parser")) == {"@type": "Place"}


def test_process_description():
    assert pedalintandem.process_description("Ride----Eat Repeat") == "Ride\nEat\nRepeat"


def test_make_event_from_ride():
    client = FakeClient(start_hour="5", start_minute="45")
    [event] = pedalintandem.make_event([soup(), NANDI], client)
    assert event["name"] == "Nandi Countryside"
    assert event["startDate"] == "2026-10-18T05:45:00+05:30"
    assert event["endDate"] == "2026-10-18T10:45:00+05:30"
    assert event["url"] == "https://www.pedalintandem.com" + NANDI
    assert event["keywords"] == ["cycle-rides-blr", "PEDALINTANDEM"]
    assert event["location"]["address"] == "nandi, bengaluru"
    assert "DISTANCE" in event["description"]
    assert client.state["ride"] == "Nandi Countryside"
    assert "Meeting Point" in client.state["itinerary"]


def test_make_event_needs_upcoming_date_and_start(monkeypatch):
    with pytest.raises(ValueError, match="no start time"):
        pedalintandem.make_event([soup(), NANDI], FakeClient())

    class Later(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 19)

    monkeypatch.setattr(pedalintandem, "date", Later)
    with pytest.raises(ValueError, match="no upcoming dates"):
        pedalintandem.make_event([soup(), NANDI], FakeClient(start_hour="5"))
