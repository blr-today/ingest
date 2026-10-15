import json

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


def test_listing_pages_each_category_until_nothing_new(monkeypatch):
    pages = {
        ("events", 1): listing_data(["e/a", "e/b"], "s"),
        ("events", 2): listing_data(["e/b"], "s"),
        ("plays", 1): listing_data(["p/c"], None),
        ("activities", 1): listing_data(["e/a", "a/d"], "t"),
        ("activities", 2): listing_data([], "t"),
    }
    calls = []

    def fake_page(category, scroll_id, page_id, bms_id):
        calls.append((category, scroll_id, page_id))
        return pages[category, page_id]

    monkeypatch.setattr(source, "listing_page", fake_page)
    monkeypatch.setattr(bookmyshow, "pause", lambda: None)
    assert [e["url"] for e in source.listing()] == ["e/a", "e/b", "p/c", "a/d"]
    assert calls == [
        ("events", None, 1),
        ("events", "s", 2),
        ("plays", None, 1),
        ("activities", None, 1),
        ("activities", "t", 2),
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
    monkeypatch.setattr(bookmyshow, "page", lambda url: html)
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
    monkeypatch.setattr(bookmyshow, "page", lambda url: None)
    assert source.page_events({"url": LINK, "startDate": "2026-11-22"}) == []


def test_events_fetch_soonest_within_budget(monkeypatch):
    listed = [{"url": u, "startDate": d} for u, d in [("c", "3"), ("a", "1"), ("b", "2")]]
    monkeypatch.setattr(source, "listing", lambda: listed)
    monkeypatch.setattr(bookmyshow, "cached", lambda url: url == "c")
    monkeypatch.setattr(source, "page_events", lambda e: [{"name": e["url"]}])
    monkeypatch.setenv("BMS_MAX_FETCHES", "1")
    assert source.events() == [{"name": "a"}, {"name": "c"}]


def test_events_fail_when_no_page_reads(monkeypatch):
    monkeypatch.setattr(source, "listing", lambda: [{"url": "a"}])
    monkeypatch.setattr(bookmyshow, "cached", lambda url: False)
    monkeypatch.setattr(source, "page_events", lambda e: [])
    with pytest.raises(RuntimeError):
        source.events()
