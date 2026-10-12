import dataclasses
import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.common.session
from src.common.shopify import Shopify
from src.sources.paintbar import COLLECTION, DOMAIN, fetch_timings, make_event, make_name, make_offers

PRODUCTS = json.loads((Path(__file__).parent / "fixtures/paintbar/products.json").read_text())
# The collection is empty today, so event titles follow the name in an old out/paintbar.json
TITLE = "Canvas, Coffee & Wine | ARAKU Coffee X Paint Bar | Sun, 19 Jul | 7:30 - 9:30 pm"


def session_for(data):
    response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: data)
    return SimpleNamespace(get=lambda url: response)


def products(data=PRODUCTS):
    return list(Shopify(DOMAIN, session_for(data), COLLECTION).products())


def test_name_drops_date_and_time():
    assert make_name(TITLE) == "Canvas, Coffee & Wine | ARAKU Coffee X Paint Bar"


def test_timings_share_the_meridiem():
    start, end = fetch_timings(TITLE)
    assert start.isoformat()[4:] == "-07-19T19:30:00+05:30"
    assert end.isoformat()[4:] == "-07-19T21:30:00+05:30"


def test_timings_with_to_and_both_meridiems():
    start, end = fetch_timings("Kids Workshop | 25 Oct | 11 am to 1 pm")
    assert (start.hour, end.hour) == (11, 13)


def test_offers_per_variant():
    offers = make_offers(products()[1])
    assert [o["price"] for o in offers] == ["5000.00", "7500.00", "8500.00", "10000.00"]
    assert offers[0]["name"] == "₹ 5000/-"


def test_make_event():
    product = dataclasses.replace(products()[0], title=TITLE)
    event = make_event(product, None)
    assert event["name"] == "Canvas, Coffee & Wine | ARAKU Coffee X Paint Bar"
    assert event["url"] == "https://www.paintbar.in/products/tropical-muse-paint-bar-diy-kit"
    assert event["offers"][0]["price"] == "1999.00"
    assert event["endDate"].endswith("T21:30:00+05:30")


def test_main_writes_events(monkeypatch, tmp_path):
    data = {"products": [dict(PRODUCTS["products"][0], title=TITLE)]}
    monkeypatch.setattr(src.common.session, "get_cached_session", lambda: session_for(data))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    runpy.run_module("src.sources.paintbar", run_name="__main__")
    [event] = json.loads((tmp_path / "out/paintbar.json").read_text())
    assert event["startDate"].endswith("T19:30:00+05:30")


def test_time_without_range_is_rejected():
    with pytest.raises(ValueError):
        fetch_timings("Kids Workshop | 25 Oct | 4 pm")
