import json
from datetime import date, datetime
from pathlib import Path

import pytest

import thewhitebox
from common.shopify import Shopify
from common.tz import IST

FIXTURE = Path(__file__).parent / "fixtures" / "thewhitebox" / "products.json"
# datefinder fills in the current year, so the fake clock follows it
YEAR = date.today().year


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(YEAR, 9, 20, tzinfo=tz)


class FakeResponse:
    encoding = None

    def raise_for_status(self):
        pass

    def json(self):
        return json.loads(FIXTURE.read_text())


class FakeSession:
    def get(self, url):
        assert url == "https://thewhiteboxco.in/collections/events-of-the-month/products.json"
        return FakeResponse()


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(thewhitebox, "datetime", Clock)


def products():
    shop = Shopify(thewhitebox.DOMAIN, FakeSession(), thewhitebox.COLLECTION)
    return {p.handle: p for p in shop.products()}


def test_announced_products_are_kept():
    kept = [p.handle for p in thewhitebox.filter_products(products().values())]
    assert kept == ["cupids-soiree-singles-mixer-new", "pottery-workshop"]


def test_variant_falls_back_to_first_title():
    mixer = products()["cupids-soiree-singles-mixer-new"]
    assert thewhitebox.bangalore_variant(mixer.variants) == mixer.variants[0].title
    mixer.variants[2].title = "Bangalore | Oct 4 | 1 PM | Brine"
    assert thewhitebox.bangalore_variant(mixer.variants) == "Bangalore | Oct 4 | 1 PM | Brine"


def test_single_time_lasts_two_hours():
    start, end = thewhitebox.fetch_timings("Early Bird - Lady's Pass / BLR | Sept 27 | 12 PM | Brine")
    assert start == datetime(YEAR, 9, 27, 12, tzinfo=IST)
    assert end == datetime(YEAR, 9, 27, 14, tzinfo=IST)


def test_date_first_title_with_range():
    start, end = thewhitebox.fetch_timings("Saturday - Oct 4 | 4-6 PM | Nolte India")
    assert start == datetime(YEAR, 10, 4, 16, tzinfo=IST)
    assert end == datetime(YEAR, 10, 4, 18, tzinfo=IST)


def test_range_with_to_and_mixed_meridians():
    start, end = thewhitebox.fetch_timings("Pass / BANGALORE | October 5 | 11 AM to 1 PM | Jamming Goat")
    assert (start.hour, end.hour) == (11, 13)


def test_far_or_malformed_titles_raise():
    with pytest.raises(ValueError):
        thewhitebox.fetch_timings("Saturday - Dec 20 | 4-6 PM | Nolte India")
    with pytest.raises(ValueError):
        thewhitebox.fetch_timings("Default Title")
    with pytest.raises(ValueError):
        thewhitebox.fetch_timings("Pass | soon | 4-6 PM")


def test_make_event_from_product():
    event = thewhitebox.make_event(products()["cupids-soiree-singles-mixer-new"], None)
    assert event["url"] == "https://thewhiteboxco.in/products/cupids-soiree-singles-mixer-new"
    assert event["startDate"] == f"{YEAR}-09-27T12:00:00+05:30"
    assert event["endDate"] == f"{YEAR}-09-27T14:00:00+05:30"
    assert [o["price"] for o in event["offers"]] == [v.price for v in products()["cupids-soiree-singles-mixer-new"].variants]
    assert event["offers"][0]["priceCurrency"] == "INR"
    assert event["description"].strip()


def test_make_event_skips_unparseable_product(capsys):
    assert thewhitebox.make_event(products()["pottery-workshop"], None) is None
    assert "Failed to parse timings" in capsys.readouterr().err


def test_time_without_meridian_is_rejected():
    with pytest.raises(ValueError, match="No AM/PM"):
        thewhitebox.fetch_timings("Saturday - Oct 4 | 4-6 | Nolte India")


def test_consecutive_past_events_are_all_dropped():
    events = [{"startDate": f"{YEAR}-09-01T12:00:00+05:30"}, {"startDate": f"{YEAR}-09-02T12:00:00+05:30"}]
    assert thewhitebox.filter_future_events(events) == []


def test_filter_future_events_drops_past_and_none():
    events = [{"startDate": f"{YEAR}-09-27T12:00:00+05:30"}, None, {"startDate": f"{YEAR}-09-01T12:00:00+05:30"}]
    assert thewhitebox.filter_future_events(events) == [{"startDate": f"{YEAR}-09-27T12:00:00+05:30"}]
