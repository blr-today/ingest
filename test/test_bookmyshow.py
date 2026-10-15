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


def test_listing_pages_until_nothing_new(monkeypatch):
    pages = {1: listing_data(["e/a", "e/b"], "s"), 2: listing_data(["e/b", "e/c"], "s")}
    pages[3] = listing_data(["e/c"], "s")
    calls = []

    def fake_page(scroll_id, page_id, bms_id):
        calls.append((scroll_id, page_id))
        return pages[page_id]

    monkeypatch.setattr(source, "listing_page", fake_page)
    monkeypatch.setattr(bookmyshow, "pause", lambda: None)
    assert [e["url"] for e in source.listing()] == ["e/a", "e/b", "e/c"]
    assert calls == [(None, 1), ("s", 2), ("s", 3)]


def test_event_prefers_page_and_drops_bms_organizer(monkeypatch):
    page = dict(EVENT, startDate="2026-11-22T17:45:00+05:30", organizer={"name": "BookMyShow"})
    html = HTML.replace(json.dumps(EVENT), json.dumps(page))
    monkeypatch.setattr(bookmyshow, "page", lambda url: html)
    summary = {"@context": "http://schema.org", "url": LINK, "startDate": "2026-11-22"}
    assert source.event(summary) == {
        "@type": "TheaterEvent",
        "url": LINK,
        "startDate": "2026-11-22T17:45:00+05:30",
        "typicalAgeRange": "8+",
        "description": "A play about\na sultan.",
    }


def test_event_needs_its_page(monkeypatch):
    monkeypatch.setattr(bookmyshow, "page", lambda url: None)
    assert source.event({"url": LINK, "startDate": "2026-11-22"}) is None


def test_events_fetch_soonest_within_budget(monkeypatch):
    listed = [{"url": u, "startDate": d} for u, d in [("c", "3"), ("a", "1"), ("b", "2")]]
    monkeypatch.setattr(source, "listing", lambda: listed)
    monkeypatch.setattr(bookmyshow, "cached", lambda url: url == "c")
    monkeypatch.setattr(source, "event", lambda e: {"name": e["url"]})
    monkeypatch.setenv("BMS_MAX_FETCHES", "1")
    assert source.events() == [{"name": "a"}, {"name": "c"}]


def test_events_fail_when_no_page_reads(monkeypatch):
    monkeypatch.setattr(source, "listing", lambda: [{"url": "a"}])
    monkeypatch.setattr(bookmyshow, "cached", lambda url: False)
    monkeypatch.setattr(source, "event", lambda e: None)
    with pytest.raises(RuntimeError):
        source.events()
