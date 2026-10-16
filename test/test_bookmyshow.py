import json
import os
import time

import pytest

from src.common import bookmyshow
from src.processors.bookmyshow import BookMyShow, _seen
from src.sources import bookmyshow as source

LINK = "https://in.bookmyshow.com/plays/tughlaq/ET00505270"
STATE = {
    "eventsSynopsisApi": {
        "queries": {
            "getPrimaryData": {
                "data": {
                    "widgets": {
                        "ABOUT_THE_EVENT": {
                            "cards": [{}, {"text": [{"text": "<p>A play about</p><p>a sultan.</p>"}]}]
                        }
                    }
                }
            }
        }
    }
}
EVENT = {"@type": "TheaterEvent", "description": "Book tickets online", "typicalAgeRange": "8+"}
HTML = (
    f'<script type="application/ld+json">[{json.dumps(EVENT)}]</script>'
    f"<script>window.__INITIAL_STATE__ = {json.dumps(STATE)};</script>"
)


def test_parse_prefers_synopsis():
    assert bookmyshow.parse(HTML) == {
        "typicalAgeRange": "8+",
        "description": "A play about\na sultan.",
    }


def test_processor_fills_only_gaps():
    _seen[LINK] = {"typicalAgeRange": "8+", "description": "About"}
    event = BookMyShow.process("u", {"sameAs": LINK, "typicalAgeRange": "16+"})
    assert event == {"sameAs": LINK, "typicalAgeRange": "16+", "description": "About"}


def test_other_links_are_ignored():
    event = {"sameAs": "https://in.bookmyshow.com/explore/plays"}
    assert BookMyShow.process("u", dict(event)) == event


def listing_data(urls, scroll_id):
    schema = [{"@context": "http://schema.org", "url": u, "name": u[-1]} for u in urls]
    return {"scrollId": scroll_id, "meta": {"ldSchema": {"eventsSchema": schema}}}


def test_listing_walks_each_listing_to_its_end(monkeypatch):
    pages = {
        ("music", 1): listing_data(["e/a", "e/b"], "s"),
        ("music", 2): listing_data(["e/b"], "s"),
        ("music", 3): listing_data(["e/c"], None),
        ("plays", 1): OSError("refused"),
        ("workshops", 1): listing_data(["e/a", "w/d"], "t"),
        ("workshops", 2): listing_data(["w/e"], "t"),
    }
    calls = []

    def fake_page(path, category, scroll_id, page_id, bms_id):
        calls.append((category or path, scroll_id, page_id))
        if isinstance(page := pages[category or path, page_id], Exception):
            raise page
        return page

    listings = [("events", "music", 9), ("plays", None, 9), ("events", "workshops", 2)]
    monkeypatch.setattr(source, "LISTINGS", listings)
    monkeypatch.setattr(source, "listing_page", fake_page)
    monkeypatch.setattr(bookmyshow, "pause", lambda: None)
    assert [e["url"] for e in source.walk()] == ["e/a", "e/b", "e/c", "w/d", "w/e"]
    assert calls == [
        ("music", None, 1),
        ("music", "s", 2),
        ("music", "s", 3),
        ("plays", None, 1),
        ("workshops", None, 1),
        ("workshops", "t", 2),
    ]


def venue(city, lat, lng):
    return {
        "name": f"Hall: {city}",
        "address": {"addressLocality": city},
        "geo": {"latitude": lat, "longitude": lng},
    }


def test_page_events_keep_bengaluru_venues(monkeypatch):
    shows = [
        dict(EVENT, startDate="2026-10-16T13:00", location=venue("Hyderabad", 17.43, 78.37)),
        dict(EVENT, startDate="2026-10-16T15:09", location=venue("Bengaluru", 12.91, 77.68)),
        dict(EVENT, startDate="2026-10-17T11:00", location={"name": "Studio: Bengaluru"}),
    ]
    shows[1]["organizer"] = {"name": "BookMyShow"}
    html = HTML.replace(f"[{json.dumps(EVENT)}]", json.dumps(shows))
    monkeypatch.setattr(bookmyshow, "load", lambda url, refresh: bookmyshow.record(url, html))
    summary = {"@context": "http://schema.org", "url": LINK, "startDate": "2026-10-16"}
    found = source.page_events(summary)
    assert [e["startDate"] for e in found] == ["2026-10-16T15:09", "2026-10-17T11:00"]
    assert found[0] == {
        "@type": "TheaterEvent",
        "url": LINK,
        "startDate": "2026-10-16T15:09",
        "location": venue("Bengaluru", 12.91, 77.68),
        "typicalAgeRange": "8+",
        "description": "A play about\na sultan.",
    }


def test_page_events_need_the_page(monkeypatch):
    monkeypatch.setattr(bookmyshow, "load", lambda url, refresh: None)
    assert source.page_events({"url": LINK, "startDate": "2026-11-22"}) == []


def test_events_fetch_soonest_within_budget(monkeypatch):
    listed = [{"url": u, "startDate": d} for u, d in [("c", "3"), ("a", "1"), ("b", "2")]]
    monkeypatch.setattr(source, "listing", lambda: listed)
    monkeypatch.setattr(bookmyshow, "cached", lambda url: url in "cd")
    monkeypatch.setattr(bookmyshow, "due", lambda url: url == "d")
    fetched = []

    def fake_events(e, refresh=False):
        fetched.extend([e["url"]] * refresh)
        return [{"name": e["url"]}]

    monkeypatch.setattr(source, "page_events", fake_events)
    monkeypatch.setenv("BMS_MAX_FETCHES", "2")
    listed.append({"url": "d", "startDate": "0"})
    assert source.events() == [{"name": u} for u in "dabc"]
    assert sorted(fetched) == ["a", "b"]
    monkeypatch.setenv("BMS_MAX_FETCHES", "1")
    fetched.clear()
    assert source.events() == [{"name": u} for u in "dac"]
    assert fetched == ["a"]


def test_events_fail_when_no_page_reads(monkeypatch):
    monkeypatch.setattr(source, "listing", lambda: [{"url": "a"}])
    monkeypatch.setattr(bookmyshow, "cached", lambda url: False)
    monkeypatch.setattr(bookmyshow, "due", lambda url: True)
    monkeypatch.setattr(source, "page_events", lambda e, refresh=False: [])
    monkeypatch.setenv("BMS_MAX_FETCHES", "1")
    with pytest.raises(RuntimeError):
        source.events()


class FakeFetcher:
    def __init__(self, bodies):
        self.bodies = list(bodies)

    def get(self, url, cache):
        if isinstance(body := self.bodies.pop(0), Exception):
            raise body
        return type("R", (), {"status_code": 200, "text": body})()


def test_page_retries_empty_shells(monkeypatch):
    shell = '{"/plays/tughlaq/ET00505270":{"status":"uninitialized"}}'
    fake = FakeFetcher([shell, HTML, shell, shell, OSError("refused"), HTML])
    monkeypatch.setattr(bookmyshow, "fetcher", lambda: fake)
    monkeypatch.setattr(bookmyshow, "pause", lambda: None)
    assert bookmyshow.page(LINK) == HTML
    assert bookmyshow.page(LINK) is None
    assert bookmyshow.page(LINK) == HTML


@pytest.fixture
def cache(monkeypatch, tmp_path):
    monkeypatch.setenv("BMS_CACHE", str(tmp_path))
    monkeypatch.setattr(bookmyshow, "today", lambda: "2026-10-16")
    return tmp_path


def show(day, city="Bengaluru"):
    lat, lng = (12.95, 77.58) if city == "Bengaluru" else (17.43, 78.37)
    return dict(EVENT, startDate=f"{day}T19:30", location=venue(city, lat, lng))


def test_pages_are_filed_under_their_soonest_bengaluru_show(cache):
    data = {"version": 1, "url": LINK, "fetched": time.time(), "synopsis": None}
    shows = [show("2026-10-17", "Hyderabad"), show("2026-11-02"), show("2026-10-20")]
    bookmyshow.save(LINK, data | {"events": shows})
    assert [p.name for p in cache.iterdir()] == ["2026-10-20-ET00505270.json"]
    bookmyshow.save(LINK, data | {"events": []})
    assert [p.name for p in cache.iterdir()] == ["9999-12-31-ET00505270.json"]
    assert bookmyshow.stored(LINK)["day"] == "9999-12-31"


def test_prune_clears_past_and_unlisted_pages(cache):
    (cache / "2026-10-15-ET1.json").write_text("{}")
    (cache / "2026-10-16-ET2.json").write_text("{}")
    (cache / "2026-10-20-ET3.json").write_text("{}")
    os.utime(cache / "2026-10-20-ET3.json", (0, 0))
    (cache / "listing.json").write_text("{}")
    assert bookmyshow.prune() == 2
    assert sorted(p.name for p in cache.iterdir()) == ["2026-10-16-ET2.json", "listing.json"]


def test_soon_shows_are_refreshed_more_often(cache):
    def filed(day, hours_ago):
        bookmyshow.save(LINK, {"version": 1, "url": LINK, "synopsis": None,
                               "fetched": time.time() - hours_ago * 3600, "events": [show(day)]})
        return bookmyshow.due(LINK)

    assert filed("2026-10-17", 7) and not filed("2026-10-17", 5)
    assert filed("2026-10-21", 25) and not filed("2026-10-21", 23)
    assert filed("2026-12-01", 73) and not filed("2026-12-01", 71)


def test_failed_refresh_keeps_the_older_copy(cache, monkeypatch):
    old = {"version": 1, "url": LINK, "synopsis": "old", "fetched": 0, "events": [show("2026-10-17")]}
    bookmyshow.save(LINK, old)
    monkeypatch.setattr(bookmyshow, "page", lambda url: None)
    assert bookmyshow.load(LINK, refresh=True)["synopsis"] == "old"
    monkeypatch.setattr(bookmyshow, "page", lambda url: HTML)
    assert bookmyshow.load(LINK, refresh=True)["synopsis"] == "A play about\na sultan."


def test_listing_round_trips_through_a_saved_file(monkeypatch, cache):
    found = [{"url": LINK, "name": "Tughlaq", "startDate": "2026-11-22"}]
    monkeypatch.setenv("BMS_CRAWL", "1")
    monkeypatch.setattr(source, "walk", lambda: found)
    assert source.listing() == found
    monkeypatch.delenv("BMS_CRAWL")
    monkeypatch.setattr(source, "walk", lambda: pytest.fail("the build must not list BMS"))
    assert source.listing() == found


def test_saved_listing_drops_foreign_entries(cache):
    events = [
        {"url": LINK, "name": "Tughlaq", "organizer": {"name": "x"}, "sameAs": "https://evil.test"},
        {"url": "https://evil.test/events/a/ET1", "name": "Bad"},
        {"url": ["not", "a", "string"]},
        "junk",
    ]
    (cache / "listing.json").write_text(json.dumps({"listed": time.time(), "events": events}))
    assert source.saved() == [{"url": LINK, "name": "Tughlaq"}]


def test_stale_listing_fails_the_source(cache):
    (cache / "listing.json").write_text(json.dumps({"listed": 0, "events": [{"url": LINK}]}))
    with pytest.raises(RuntimeError):
        source.saved()


def test_builds_from_a_saved_listing_only_read_the_cache(monkeypatch):
    monkeypatch.delenv("BMS_CRAWL", raising=False)
    monkeypatch.delenv("BMS_MAX_FETCHES", raising=False)
    monkeypatch.setattr(source, "listing", lambda: [{"url": "a"}, {"url": "b"}])
    monkeypatch.setattr(bookmyshow, "cached", lambda url: url == "b")
    monkeypatch.setattr(bookmyshow, "due", lambda url: True)
    monkeypatch.setattr(source, "page_events", lambda e, refresh=False: [{"name": e["url"], "refresh": refresh}])
    assert source.events() == [{"name": "b", "refresh": False}]


def test_parse_prefers_the_bengaluru_show():
    shows = [
        dict(EVENT, typicalAgeRange="18+", location=venue("Hyderabad", 17.43, 78.37)),
        dict(EVENT, location=venue("Bengaluru", 12.95, 77.58)),
    ]
    html = HTML.replace(f"[{json.dumps(EVENT)}]", json.dumps(shows))
    assert bookmyshow.parse(html)["typicalAgeRange"] == "8+"
