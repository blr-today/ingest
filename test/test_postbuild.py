import json
import sqlite3
from pathlib import Path

import pytest

from src import tagger
from src.processors.__main__ import should_process_url
from src.processors.allevents import AllEvents
from src.processors.eventtype import EventType

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "test/fixtures/postbuild"

pytestmark = pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 38), reason="post-build.sql needs ->>"
)


def rows(db):
    with sqlite3.connect(db) as conn:
        found = conn.execute("SELECT url, event_json FROM events ORDER BY rowid")
        return {url: json.loads(event) for url, event in found}


def postbuild(events, db):
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE events (url TEXT, event_json TEXT)")
        conn.executemany(
            "INSERT INTO events VALUES (?, ?)",
            [(e["url"], json.dumps(e)) for e in events],
        )
        conn.executescript((REPO / "post-build.sql").read_text())
    return rows(db)


def tag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.setattr(tagger, "CACHE", tmp_path / "activities.sqlite")
    tagger.main()
    return rows(tmp_path / "events.db")


def test_sports_screening(tmp_path, monkeypatch):
    events = json.loads((FIXTURES / "sports_screening.json").read_text())
    postbuild(events, tmp_path / "events.db")
    got = {url: sorted(e["keywords"]) for url, e in tag(tmp_path, monkeypatch).items()}
    # SQL once tagged low-quality too; the tagger skips events with EXCLUDE tags
    expected = FIXTURES / "sports_screening.expected.json"
    assert got == json.loads(expected.read_text())


def test_allevents_rows_keep_eventtype_types(tmp_path):
    events = json.loads((FIXTURES / "allevents.json").read_text())
    for event in events:
        for processor in (AllEvents, EventType):
            assert should_process_url(processor, event["url"])
            processor.process(event["url"], event)
    got = postbuild(events, tmp_path / "events.db")
    assert [e.get("@type") for e in got.values()] == [
        "SocialEvent",
        "MusicEvent",
        "Event",
        "BusinessEvent",
    ]


def test_city_wide_venues_lose_their_geo(tmp_path):
    def event(url, name, lat, lng):
        geo = {"latitude": lat, "longitude": lng}
        return {
            "url": url,
            "name": "Run",
            "keywords": [],
            "location": {"name": name, "geo": geo},
        }

    got = postbuild(
        [
            event("https://a.in/1", "Bengaluru", 13.25, 77.71),
            event("https://a.in/2", "", 12.9628957, 77.57754),
            event("https://a.in/3", "Cubbon Park", 12.97425, 77.59219),
        ],
        tmp_path / "events.db",
    )
    assert [bool(e["location"].get("geo")) for e in got.values()] == [
        False,
        False,
        True,
    ]


def test_bms_craft_menus_are_low_quality(tmp_path):
    def bms(name, venue, start="2026-10-24T12:00:00+05:30", kind="EducationEvent"):
        return {
            "url": f"https://in.bookmyshow.com/events/{name}/ET1",
            "@type": kind,
            "name": name,
            "startDate": start,
            "location": {"name": venue},
            "keywords": ["BOOKMYSHOW"],
        }

    bar = "21st Amendment Gastrobar: Indiranagar"
    menu = [bms(n, bar) for n in ("sip-and-paint", "clay-lighter", "kintsugi")]
    alone = [
        bms("pottery", "Clay Station"),
        bms("resin", "Clay Station"),
        bms("later", bar, start="2026-10-24T15:00:00+05:30"),
        bms("comedy", bar, kind="ComedyEvent"),
    ]
    got = postbuild(menu + alone, tmp_path / "events.db")
    low = {e["name"] for e in got.values() if "LOW-QUALITY" in e["keywords"]}
    assert low == {"sip-and-paint", "clay-lighter", "kintsugi"}


def test_odyssey_vibes_venue_is_low_quality(tmp_path):
    event = {
        "url": "https://in.bookmyshow.com/events/open-talk-with-nishi/ET00386447",
        "name": "Candid Conversations with Nishi",
        "location": {"name": "Odyssey Vibes: Bengaluru"},
        "keywords": ["BOOKMYSHOW"],
    }
    got = postbuild([event], tmp_path / "events.db")
    assert "LOW-QUALITY" in got[event["url"]]["keywords"]


def test_small_world_is_low_quality(tmp_path):
    def bms(code, description):
        return {
            "url": f"https://in.bookmyshow.com/events/{code}",
            "description": description,
            "keywords": ["BOOKMYSHOW"],
        }

    events = [
        bms("perfumery/ET00469072", "Join Small World for a perfumery session"),
        bms("couple-dance-workshop/ET00417785", "Discover the Joy of Partner Dancing"),
        bms("songs/ET1", "Songs about a small world"),
    ]
    got = postbuild(events, tmp_path / "events.db")
    low = [url for url, e in got.items() if "LOW-QUALITY" in e["keywords"]]
    assert low == [e["url"] for e in events[:2]]


def test_bms_pay_at_venue_workshops_are_low_quality(tmp_path):
    def bms(code, kind, ticket):
        offer = {"@type": "Offer", "name": ticket, "price": "799.00"}
        return {
            "url": f"https://in.bookmyshow.com/events/{code}",
            "@type": kind,
            "offers": {"@type": "AggregateOffer", "offers": [offer]},
            "keywords": ["BOOKMYSHOW"],
        }

    events = [
        bms("beach-candle/ET00492214", "EducationEvent", "PASS+300PAYATAVENUE"),
        bms("resin-shaker/ET00521901", "EducationEvent", "PASS + 99 PAY AT VENUE"),
        bms("sama-halloween/ET00521551", "Event", "ENTRY+500 PAY AT VENUE"),
        bms("pottery/ET1", "EducationEvent", "ENTRY PASS"),
    ]
    got = postbuild(events, tmp_path / "events.db")
    low = [url for url, e in got.items() if "LOW-QUALITY" in e["keywords"]]
    assert low == [e["url"] for e in events[:2]]


def test_urbanaut_hosts_skip_curation(tmp_path):
    def spot(slug, host, name, start, keywords=()):
        return {
            "url": f"https://urbanaut.app/spot/{slug}#{start}",
            "name": name,
            "startDate": start,
            "organizer": {"name": host, "url": f"https://urbanaut.app/partner/{host}"},
            "keywords": ["URBANAUT", *keywords],
        }

    events = [
        spot("walk", "benbyfoot", "Fort walk", "2026-11-01", ["Walking Tour"]),
        spot("jam", "benbyfoot", "Fort walk", "2026-11-08", ["Walking Tour"]),
        spot("pasta", "canellastudio", "Pasta", "2026-11-01", ["Workshop"]),
        spot("dinner", "somechef", "Supper Club", "2026-11-01", ["Food & drink"]),
        spot("gig", "somebar", "Jazz Dinner", "2026-11-01", ["Food & drink", "Music"]),
        spot("ai", "somecoach", "AI | Online", "2026-11-01", ["Virtual"]),
    ]
    got = postbuild(events, tmp_path / "events.db")
    skipped = [url for url, e in got.items() if "-CURATED" in e["keywords"]]
    assert skipped == [events[i]["url"] for i in (1, 2, 3, 5)]


def test_certification_courses_are_business(tmp_path):
    url = "https://allevents.in/bangalore/leading-safe-60-scaled-agilist-certification-training-in-worcester-ma/100001996177936945"
    safe = {
        "url": url,
        "name": "Leading SAFe 6.0 (Scaled Agilist) Certification Training in Worcester, MA",
        "keywords": ["ALLEVENTS"],
        "location": {"name": "Regus Business Center", "address": {"addressLocality": "Bangalore"}},
        "organizer": [{"@type": "Organization", "name": "Lean Education Inc."}],
    }
    pmp = safe | {"url": "https://allevents.in/x/1", "name": "PMP Bootcamp"}
    got = postbuild([safe, pmp], tmp_path / "events.db")
    assert "BUSINESS" in got[url]["keywords"]
    assert "BUSINESS" in got["https://allevents.in/x/1"]["keywords"]


def test_offlyn_curation(tmp_path):
    def listing(slug, host, name, keywords=(), description=""):
        return {
            "url": f"https://offlyn.life/e/{slug}",
            "name": name,
            "description": description,
            "organizer": {"@type": "Organization", "name": host},
            "keywords": ["OFFLYN", *keywords],
        }

    events = [
        listing("a", "Couch Potato", "Diwali House Party", ["Party"]),
        listing("b", "Prakriti", "Ghar Waali Diwali", ["Social Mixer"]),
        listing("c", "akanksha", "Dhikchik Diwali", ["Networking"], "a little Diwali house party at my place"),
        listing("d", "The Art Nook", "The Diwali Edit", ["Workshop"]),
        listing("e", "Girly-Verse", "Potluck", ["Party"]),
        listing("f", "Pint of View", "Lecture #124", ["Talk / Panel"]),
        listing("g", "Varun", "Sway", ["Dating / Singles Mixer"]),
        listing("h", "Vantage Point 78 by Primate Advisory", "Design Thinking Bootcamp"),
    ]
    club = {"url": "https://highape.com/x", "name": "Diwali Party", "keywords": ["HIGHAPE"]}
    got = postbuild(events + [club], tmp_path / "events.db")

    def tagged(tag):
        return [url[-1] for url, e in got.items() if tag in e["keywords"]]

    assert tagged("LOW-QUALITY") == ["a", "b", "c", "g"]
    assert tagged("WOMEN-ONLY") == ["e"]
    assert tagged("CURATED") == ["f"]
    assert tagged("BUSINESS") == ["h"]
