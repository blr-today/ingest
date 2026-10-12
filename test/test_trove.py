import datetime
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

import common.session
from common.shopify import Shopify
from trove import COLLECTION, DOMAIN, fetch_timings, get_date_str, get_location, get_subtitle, make_event, make_offers
from common.tz import IST

d = datetime.datetime

DATE_FIXTURES = [
    ['Sat | Jun 29 | 10 AM - 12:30 PM', d(2024, 6, 29, 10, 0, tzinfo=IST), d(2024, 6, 29, 12, 30, tzinfo=IST)],
    ['Sat | Jun 29 | 3 - 6 PM', d(2024, 6, 29, 15, 0, tzinfo=IST), d(2024, 6, 29, 18, 0, tzinfo=IST)],
    ['Sun | Jun 30 | 9:30 -11:30 AM', d(2024, 6, 30, 9, 30, tzinfo=IST), d(2024, 6, 30, 11, 30, tzinfo=IST)],
    ['Sun | Jun 30 | 11 AM - 1 PM', d(2024, 6, 30, 11, 0, tzinfo=IST), d(2024, 6, 30, 13, 0, tzinfo=IST)],
    ['Sat | Jul 06 | 4 - 6:30 PM', d(2024, 7, 6, 16, 0, tzinfo=IST), d(2024, 7, 6, 18, 30, tzinfo=IST)],
    ['Sun | Jul 07 | 8:30 AM to 11:30 AM', d(2024, 7, 7, 8, 30, tzinfo=IST), d(2024, 7, 7, 11, 30, tzinfo=IST)],
    ['Sun | Jul 07 | 10 AM to 12:30 PM', d(2024, 7, 7, 10, 0, tzinfo=IST), d(2024, 7, 7, 12, 30, tzinfo=IST)],
    ['Sun | Jul 14 | 10:30 AM - 1 PM', d(2024, 7, 14, 10, 30, tzinfo=IST), d(2024, 7, 14, 13, 0, tzinfo=IST)],
    ['Sun | Jul 14 | 4 - 7 PM', d(2024, 7, 14, 16, 0, tzinfo=IST), d(2024, 7, 14, 19, 0, tzinfo=IST)]
]

class TestFetch:
    def test_time_splits(self):
        for date_str, expected_start, expected_end in DATE_FIXTURES:
            start_d, end_d = fetch_timings(date_str)
            # datefinder infers the nearest year, so ignore it
            assert start_d.replace(year=2024) == expected_start
            assert end_d.replace(year=2024) == expected_end


FIXTURES = Path(__file__).parent / "fixtures/trove"


class FakeSession:
    def get(self, url):
        name = "products.json" if url.endswith("products.json") else url.split("/")[-1] + ".html"
        text = (FIXTURES / name).read_text()
        return SimpleNamespace(text=text, raise_for_status=lambda: None, json=lambda: json.loads(text))


def products():
    return list(Shopify(DOMAIN, FakeSession(), COLLECTION).products())


def soup(name):
    return BeautifulSoup((FIXTURES / name).read_text(), "html.parser")


def test_page_fields():
    page = soup("wine-tasting-experience-bangalore.html")
    assert get_date_str(page) == "Sun | Sep 27 | 4 - 6 PM"
    assert get_subtitle(page) == "Decoding Fine Wines"
    assert get_location(page) == ("Toscano", "Jayanagar 1st Block, Bangalore")


def test_missing_page_fields():
    page = BeautifulSoup("<div class='custom-field__location'>Indiranagar</div>", "html.parser")
    assert get_date_str(page) is None
    assert get_subtitle(page) is None
    assert get_location(page) == ("Indiranagar", None)
    assert get_location(BeautifulSoup("<div class='custom-field__location'> </div>", "html.parser")) is None


def test_offers_use_variant_sku():
    [offer] = make_offers(products()[0])
    assert offer["priceCurrency"] == "INR"
    assert offer["price"] == "2000.00"
    assert offer["sku"]


def test_make_event_reads_product_page():
    event = make_event(products()[0], None, FakeSession())
    assert event["name"] == "Summit Seekers - A Rock Climbing Experience"
    assert event["url"] == "https://troveexperiences.com/products/rock-climbing-in-bangalore"
    assert event["startDate"][4:] == "-09-27T11:00:00+05:30"
    assert event["endDate"][4:] == "-09-27T13:00:00+05:30"
    assert event["location"] == {"@type": "Place", "name": "Svadhyaya's Learning Space", "address": "Jayanagar, Bangalore"}


def test_make_event_skips_pages_without_date():
    session = SimpleNamespace(get=lambda url: SimpleNamespace(text="<html></html>"))
    assert make_event(products()[0], None, session) is None


def test_main_writes_events(monkeypatch, tmp_path):
    monkeypatch.setattr(common.session, "get_cached_session", FakeSession)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    runpy.run_module("trove", run_name="__main__")
    events = json.loads((tmp_path / "out/trove.json").read_text())
    assert [e["location"]["name"] for e in events] == ["Svadhyaya's Learning Space", "Toscano"]


def test_date_without_time_is_rejected():
    with pytest.raises(ValueError):
        fetch_timings("Sat | Jun 29")
