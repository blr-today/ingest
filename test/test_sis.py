import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import sis
from common.tz import IST

FIXTURES = Path(__file__).parent / "fixtures" / "sis"


class Clock(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 12, 12, 0, tzinfo=tz)


class FakeResponse:
    def __init__(self, text, status=200):
        self.text = text
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise RuntimeError(self.status)


class FakeSession:
    def __init__(self):
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        path = FIXTURES / f"{url.rsplit('/', 1)[-1]}.html"
        return FakeResponse(path.read_text() if path.exists() else "<html></html>")


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(sis, "datetime", SimpleNamespace(datetime=Clock, timedelta=datetime.timedelta))


@pytest.fixture
def cards():
    return {c["slug"]: c for c in sis.fetch_cards(FakeSession())}


def test_cards_come_from_split_rsc_chunks(cards):
    assert list(cards) == [
        "Women-Bangalore-TCS-ART",
        "Sisters-Misters-Bangalore-Football-Game-Day-Sunday6",
        "Women-Bangalore-Yoga-Sisters-Misters",
        "Women-Bangalore-Badminton-Combined",
    ]


def test_balanced_array_handles_brackets_in_strings():
    assert sis.extract_balanced_array('{"cards":[{"t":"a]\\"[b"},[1]],"x":1}', "cards") == [{"t": 'a]"[b'}, [1]]
    assert sis.extract_balanced_array('{"other":[]}', "cards") is None
    assert sis.extract_balanced_array('{"cards":[1,2', "cards") is None


def test_product_details_read_end_time():
    assert sis.fetch_product_details(FakeSession(), "Women-Bangalore-TCS-ART") == (None, "5:00 pm")
    assert sis.fetch_product_details(FakeSession(), "missing") == (None, None)


def test_product_details_read_address():
    page = '<script>self.__next_f.push([1,"[\\"rt-0-0\\",{\\"children\\":\\"SUFC Gate No. 3, Ulsoor\\"}]"])</script>'
    session = SimpleNamespace(get=lambda url: FakeResponse(page))
    assert sis.fetch_product_details(session, "x") == ("SUFC Gate No. 3, Ulsoor", None)


def test_end_time_rolls_past_midnight():
    start = Clock(2026, 10, 17, 23, 0, tzinfo=IST)
    assert sis.parse_end_time(start, "1:00 am").isoformat() == "2026-10-18T01:00:00+05:30"
    assert sis.parse_end_time(start, "late") is None


def test_single_workshop_gets_end_time(cards):
    [event] = sis.make_events(FakeSession(), cards["Women-Bangalore-TCS-ART"])
    assert event["@type"] == "SportsEvent"
    assert event["sport"] == "Art Workshop"
    assert event["startDate"] == "2026-10-17T15:00:00+05:30"
    assert event["endDate"] == "2026-10-17T17:00:00+05:30"
    assert event["offers"] == [{"@type": "Offer", "price": "950", "priceCurrency": "INR"}]
    assert event["isAccessibleForFree"] is False
    assert event["url"] == "https://sistersinsweat.com/bengaluru/products/Women-Bangalore-TCS-ART"
    assert event["image"].startswith("https://sistersinsweat.com/api/media/file/")
    assert event["keywords"] == ["SISTERSINSWEAT", "SISTERSINSWEAT/SPORTS"]
    assert "location" not in event


def test_recurring_session_is_capped(cards):
    events = sis.make_events(FakeSession(), cards["Sisters-Misters-Bangalore-Football-Game-Day-Sunday6"])
    assert [e["startDate"][:10] for e in events] == ["2026-10-18", "2026-10-25", "2026-11-01", "2026-11-08"]
    assert events[0]["startDate"] == "2026-10-18T07:30:00+05:30"
    assert all("endDate" not in e for e in events)


def test_yoga_is_a_social_session(cards):
    event = sis.make_events(FakeSession(), cards["Women-Bangalore-Yoga-Sisters-Misters"])[0]
    assert event["@type"] == "SocialEvent"
    assert event["keywords"] == ["SISTERSINSWEAT", "SISTERSINSWEAT/SESSION"]
    assert "sport" not in event


def test_location_needs_venue_and_address(cards, monkeypatch):
    monkeypatch.setattr(sis, "fetch_product_details", lambda session, slug: ("Indiranagar Double Road", None))
    event = sis.make_events(FakeSession(), cards["Women-Bangalore-Badminton-Combined"])[0]
    assert event["sport"] == "Badminton"
    assert event["location"]["name"] == "Game Theory, Double Road, Indiranagar"
    assert event["location"]["address"] == "Indiranagar Double Road"


def test_packages_and_virtual_sessions_are_skipped(cards):
    card = cards["Women-Bangalore-TCS-ART"]
    assert sis.make_events(FakeSession(), dict(card, slug="Women-Package-Detail")) == []
    assert sis.make_events(FakeSession(), dict(card, title="Monthly Subscription")) == []
    assert sis.make_events(FakeSession(), dict(card, venueName="Virtual (Zoom)")) == []


def test_guess_sport_from_slug():
    assert sis.guess_sport({"activityName": "$undefined"}, "Women-Bangalore-Frisbee") == "Frisbee"
    assert sis.guess_sport({}, "Women-Bangalore-Running-Club") == "Running"
    assert sis.guess_sport({}, "Women-Bangalore-Social") is None
