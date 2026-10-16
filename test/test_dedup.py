import json
import sqlite3
from pathlib import Path

from src.dedup import (
    AGGREGATORS,
    RANKED,
    as_list,
    combine_offers,
    core_title,
    dedup,
    fill,
    geo,
    hidden,
    is_duplicate,
    links,
    merge,
    name_session,
    normalize,
    offer_list,
    promote,
    rank,
    same_lineup,
    same_session,
)

STUDIO = {"@type": "Place", "name": "New York dance classes"}


def nydc(name, url):
    return {"name": name, "url": url, "location": STUDIO}


def test_one_studio_merges_same_style():
    a = nydc("Garba & Dandiya Dance Workshop @ NYDC", "https://highape.com/a")
    b = nydc("NYDC Garba and Dandiya Workshop for Beginners", "https://district.in/b")
    assert is_duplicate(a, b)


def test_one_studio_keeps_other_styles():
    a = nydc("Heels Dance Workshop for Beginners", "https://district.in/a")
    b = nydc("Lap Couple Dance Workshop For Beginner", "https://district.in/b")
    assert not is_duplicate(a, b)


def test_other_venues_need_matching_titles():
    a = {"name": "Garba Night", "url": "https://x.in/a", "location": {"name": "Hall"}}
    b = {
        "name": "Garba Workshop",
        "url": "https://y.in/b",
        "location": {"name": "Hall"},
    }
    assert not is_duplicate(a, b)


def listing(name, venue, lat, lng, keywords=()):
    return {
        "name": name,
        "url": f"https://www.district.in/events/{name.lower().replace(' ', '-')}",
        "organizer": {"name": "Getaway Technologies Private Limited"},
        "location": {"name": venue, "geo": {"latitude": lat, "longitude": lng}},
        "keywords": list(keywords),
    }


def test_one_host_session_merges_across_venue_names():
    a = listing(
        "Kintsugi Workshop in HSR Layout", "Tim Hortons India", 12.9120662, 77.6470938
    )
    b = listing("SIP and PAINT", "Tim Hortons | HSR, Bangalore", 12.9121, 77.647)
    assert same_session(a, b)


def test_session_needs_same_place_and_visibility():
    a = listing("Sip and Clay", "URU - JP Nagar", 12.9057826, 77.6011616)
    b = listing("Sip and Paint", "URU - Whitefield", 12.9613421, 77.7325235)
    c = listing(
        "Mafia Night", "URU - JP Nagar", 12.9057826, 77.6011616, ["LOW-QUALITY"]
    )
    assert not same_session(a, b)
    assert not same_session(a, c)


def test_far_apart_listings_stay_separate():
    church = listing("Sip and Clay", "Third Wave Coffee", 12.974659, 77.6067528)
    indiranagar = listing("Sip and Paint", "Third Wave Coffee", 12.9702038, 77.6386734)
    assert not same_session(church, indiranagar)
    mafia = listing(
        "Mafia Night", "Tim Hortons, Phoenix Mall of Asia", 13.0709, 77.5925
    )
    other = dict(
        listing("Mafia Night", "Buddiezz Cafe", 12.937938, 77.6261241),
        url="https://in.bookmyshow.com/x",
    )
    assert not is_duplicate(mafia, other)
    assert not is_duplicate(mafia, dict(other, sameAs=[mafia["url"]]))


def test_session_name_lists_choices():
    event = {"name": "Sip and Clay", "description": "Bring a friend."}
    name_session(event, ["Sip and Clay", "Sip and Paint", "Kintsugi"])
    assert event["name"] == "Sip and Clay and 2 more"
    assert event["description"].startswith(
        "Choose from: Sip and Clay; Sip and Paint; Kintsugi."
    )


ROWS = json.loads((Path(__file__).parent / "fixtures/dedup/events.json").read_text())


def run(tmp_path, rows):
    db = tmp_path / "events.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE events (url TEXT, event_json TEXT)")
    conn.executemany(
        "INSERT INTO events VALUES (?, ?)", [(u, json.dumps(e)) for u, e in rows]
    )
    conn.commit()
    dedup(str(db))
    return {
        u: json.loads(e) for u, e in conn.execute("SELECT url, event_json FROM events")
    }


def test_rank_and_titles():
    assert rank("https://www.district.in/x") == 1
    assert rank("https://puttingscene.com/events/1") == len(AGGREGATORS) + 1
    assert rank("https://courtyardkoota.com/events/x/") == 0
    assert normalize("Rock ’n’ Roll -- Night!") == "rock n roll night"
    assert (
        core_title("Rage Room | Bengaluru")
        == core_title("Rage Room - Bangalore")
        == "rage room"
    )
    assert core_title("Pop Culture Quiz by Calm Your Wits") == "pop culture quiz"


def test_links_ignore_scheme_and_case():
    a = {
        "url": "https://www.Penciljam.com/main/events/x/",
        "sameAs": ["http://a.in/%7Eb", 5],
    }
    assert links(a) == {"penciljam.com/main/events/x", "a.in/~b"}
    assert is_duplicate({"name": "A", "url": "https://penciljam.com/main/events/x"}, a)


def test_instagram_posts_match_across_url_forms():
    ours = {"name": "Jazz Night", "url": "https://www.instagram.com/p/DUVqs5OEnwS/"}
    for link in [
        "https://www.instagram.com/p/DUVqs5OEnwS/?img_index=1",
        "https://instagram.com/reel/DUVqs5OEnwS",
        "https://www.instagram.com/af_bangalore/p/DUVqs5OEnwS/",
    ]:
        assert is_duplicate({"name": "Other", "url": "https://a.in/1", "sameAs": link}, ours)
    assert rank("https://www.instagram.com/p/x/") == len(RANKED)


def test_titles_must_overlap_enough():
    def dup(x, y):
        return is_duplicate(
            {"name": x, "url": "https://a.in/1"}, {"name": y, "url": "https://b.in/2"}
        )

    assert dup("Rage Room | Bengaluru", "Rage Room | Bangalore")
    assert dup("Horn OK Quiz", "Horn OK Quiz!")
    assert dup(
        "Screening of Amour (2012)", "Screening of Amour (2012) with Cinema Next Door"
    )
    assert not dup("Amour", "Screening of Amour")
    assert not dup("", "Amour")
    assert not dup("- Rage Room", "- Rage Room Bengaluru")
    assert dup("Dark and Late Comedy show", "Dark & Late Comedy Show")
    assert dup(
        "Office chugli stand-up comedy crowd work show",
        "Office Chugli Standup Comedy Crowdwork Show",
    )


def test_improv_lore_always_merges():
    a = {
        "name": "The Silliest Show Tonight by Improv Lore",
        "url": "https://district.in/a",
    }
    b = {
        "name": "Friday Show",
        "url": "https://a.in/b",
        "organizer": {"name": "Improv Lore"},
    }
    assert is_duplicate(a, b)


def test_hidden_and_geo():
    assert hidden({"keywords": "DISTRICT,LOW-QUALITY"})
    assert not hidden({"keywords": ["DISTRICT"]})
    assert geo({"location": {"geo": {"latitude": "12.9", "longitude": "77.6"}}}) == (
        12.9,
        77.6,
    )
    assert geo({"location": {"geo": {"latitude": "?"}}}) is None
    assert geo({"location": "Koota"}) is None


def test_session_needs_a_shared_activity():
    venue = ("Bloom Creative Zone - Haralur", 12.9034889, 77.6621356)
    paint = listing(
        "Acrylic Painting Workshop", *venue, ["ART-CRAFT", "PAINTING-SKETCHING"]
    )
    clay = listing("Clay Crafting Workshop", *venue, ["ART-CRAFT", "POTTERY"])
    dance = listing("Semi Classical Dance Workshop", *venue, ["DANCE-CLASS"])
    assert same_session(paint, clay)
    assert not same_session(paint, dance)
    assert same_session(paint, listing("Mystery Workshop", *venue))


def test_session_needs_an_aggregator_and_organizer():
    a = listing("Sip and Clay", "URU - JP Nagar", 12.9, 77.6)
    b = listing("Sip and Paint", "URU - JP Nagar", 12.9, 77.6)
    assert same_session(a, b)
    assert not same_session(a | {"url": "https://courtyardkoota.com/x"}, b)
    assert not same_session(a | {"organizer": {}}, b | {"organizer": {}})


def test_fill_only_adds():
    kept = {
        "name": "A",
        "image": ["x"],
        "offers": [],
        "location": {"@type": "Place", "name": "Koota"},
    }
    other = {
        "name": "B",
        "image": ["x", "y"],
        "offers": [{"price": 1}],
        "description": "",
        "location": {"@type": "Place", "address": "Jayanagar"},
        "organizer": {"name": "O"},
    }
    fill(kept, other)
    assert kept == {
        "name": "A",
        "image": ["x", "y"],
        "offers": [{"price": 1}],
        "location": {"@type": "Place", "name": "Koota", "address": "Jayanagar"},
        "organizer": {"name": "O"},
    }
    kept = {"location": {"@type": "Place", "name": "Koota"}}
    fill(kept, {"location": {"@type": "VirtualLocation", "url": "u"}})
    assert kept == {"location": {"@type": "Place", "name": "Koota"}}


def test_offers_are_kept_once_per_price():
    kept = {"offers": [{"price": "500"}, {"name": "TBA"}]}
    dropped = {"offers": {"price": 500.0, "name": "Stag"}}
    assert combine_offers(kept, dropped) == kept["offers"]
    dropped = {
        "offers": [{"price": "500", "priceCurrency": "USD"}, {"name": "TBA"}, "x"]
    }
    assert combine_offers(kept, dropped) == kept["offers"] + [
        {"price": "500", "priceCurrency": "USD"}
    ]
    assert offer_list(None) == [] and as_list(None) == []


def test_merge_combines_listings():
    kept = {
        "@type": "Event",
        "url": "https://district.in/a",
        "keywords": "DISTRICT, PRICEY",
        "image": "a.png",
    }
    dropped = {
        "@type": "ScreeningEvent",
        "url": "https://highape.com/b",
        "keywords": ["HIGHAPE", "BUDGET", ""],
        "image": ["b.png", "a.png"],
        "sameAs": ["https://district.in/a", "https://ig.com/b"],
        "description": "From HighApe",
    }
    merge(kept, dropped, "https://highape.com/b")
    assert kept["@type"] == "ScreeningEvent"
    assert kept["keywords"] == ["DISTRICT", "PRICEY", "HIGHAPE"]
    assert kept["sameAs"] == ["https://highape.com/b", "https://ig.com/b"]
    assert kept["image"] == ["a.png", "b.png"]
    assert kept["description"] == "From HighApe"
    assert "offers" not in kept


def test_merge_keeps_identifier_with_its_source():
    kept = {"url": "https://highape.com/a"}
    merge(kept, {"url": "https://skillboxes.com/b", "identifier": "com.skillboxes.1"}, "b")
    assert "identifier" not in kept


def test_merge_reprices_from_both_offers():
    kept = {"url": "k", "keywords": ["PRICEY"], "offers": {"price": "2500"}}
    merge(kept, {"offers": [{"price": "300"}]}, "d")
    assert kept["offers"] == [{"price": "2500"}, {"price": "300"}]
    assert kept["keywords"] == ["BUDGET"]
    kept = {"url": "k", "@type": "MusicEvent", "image": "a"}
    merge(
        kept, {"@type": "Event", "offers": {"price": "0"}, "image": {"url": "b"}}, "d"
    )
    assert kept["offers"] == {"price": "0"} and kept["keywords"] == ["FREE"]
    assert kept["@type"] == "MusicEvent" and kept["image"] == ["a"]
    kept = {"url": "k", "offers": {"price": "0"}}
    merge(kept, {"offers": {"price": 0}}, "d")
    assert kept["offers"] == {"price": "0"}


def test_curators_promote_the_organiser_page():
    event = {
        "url": "https://puttingscene.com/events/1",
        "sameAs": [
            "mailto:a@b.in",
            "https://district.in/x",
            "https://m.facebook.com/e",
            "https://koota.in/e",
        ],
    }
    assert promote(event)
    assert event["url"] == "https://koota.in/e"
    assert event["sameAs"] == [
        "https://puttingscene.com/events/1",
        "mailto:a@b.in",
        "https://district.in/x",
        "https://m.facebook.com/e",
    ]
    assert not promote({"url": "https://district.in/a", "sameAs": "https://koota.in/e"})
    assert not promote(
        {"url": "https://tonight.is/a", "sameAs": ["https://instagram.com/p/1"]}
    )


def test_dedup_scraped_listings(tmp_path, capsys):
    events = run(tmp_path, ROWS)
    assert len(events) == len(ROWS) - 1
    rage = events["https://district.in/rage-room-bangalore-2025/event"]
    assert rage["sameAs"] == [ROWS[1][0]]
    assert rage["keywords"] == [
        "DISTRICT",
        "INDIRANAGAR",
        "INSIDER",
        "LOW-QUALITY",
        "HIGHAPE",
        "BUDGET",
    ]
    assert len(rage["image"]) == 2 and len(rage["offers"]) == 2
    # Two Amoeba branches on one site stay apart
    assert "https://district.in/amoeba-itpl-bengaluru-jun-2025/event" in events
    trove = events["https://puttingscene.com/events/2908"]
    assert trove["url"].startswith("https://troveexperiences.com/")
    assert trove["sameAs"] == ["https://puttingscene.com/events/2908"]
    assert events["https://puttingscene.com/events/2918"] == ROWS[6][1]
    assert "Removed 1 duplicate events" in capsys.readouterr().out


def test_dedup_names_sessions(tmp_path):
    rows = []
    for name in ("Sip and Clay", "Sip and Paint", "Kintsugi"):
        event = listing(name, "URU - JP Nagar", 12.9057826, 77.6011616)
        rows.append((event["url"], event | {"startDate": "2026-10-17T16:00:00+05:30"}))
    rows.append(("https://district.in/undated", {"name": "No date"}))
    events = run(tmp_path, rows)
    assert len(events) == 2
    session = events[rows[0][0]]
    assert session["name"] == "Sip and Clay and 2 more"
    assert (
        session["description"] == "Choose from: Sip and Clay; Sip and Paint; Kintsugi."
    )


def test_dedup_rounds_one_room_slots(tmp_path):
    a = nydc("Salsa Workshop", "https://district.in/a") | {
        "startDate": "2026-10-17T18:05:00+05:30"
    }
    b = nydc("Salsa Bootcamp", "https://district.in/b") | {
        "startDate": "2026-10-17T18:10:00+05:30"
    }
    c = nydc("Salsa Social", "https://district.in/c") | {
        "startDate": "2026-10-17T18:20:00+05:30"
    }
    events = run(tmp_path, [(e["url"], e) for e in (a, b, c)])
    assert set(events) == {"https://district.in/a", "https://district.in/c"}


def comedy(name, performers, venue="The Comedy Theatre, Indiranagar: Bengaluru"):
    event = listing(name, venue, 12.9701, 77.6393)
    del event["organizer"]
    people = [{"@type": "Person", "name": p} for p in performers]
    return event | {"url": f"https://in.bookmyshow.com/{name}", "performer": people}


def test_shared_lineup_is_one_slot():
    dark = comedy("Dark Jokes", ["Adel Rahman", "Kush Patel", "Arvind Sunder"])
    sex = comedy("Sex Jokes Night", ["Adel Rahman", "Kush Patel", "Harman Singh"])
    midnight = comedy("Mid-night Comedy", ["Himanshu Bhardwaj", "Adel Rahman"])
    assert same_lineup(dark, sex) and same_session(dark, sex)
    assert not same_lineup(dark | {"performer": []}, sex)
    assert not same_lineup(dark, midnight | {"performer": [{"name": "Rupali"}]})
    next_door = comedy("Live Stand Up Comedy", ["Adel Rahman"], "TAG Comedy Club")
    assert not same_lineup(dark, next_door)
    various = {"performer": {"name": "Various Artists"}}
    assert not same_lineup(dark | various, sex | various)


def test_dedup_joins_one_lineup_across_sites(tmp_path):
    start = {"startDate": "2026-10-17T17:00:00+05:30"}
    chugli = comedy("Office chugli stand-up comedy crowd work show", ["Anmol Garg"])
    gossip = comedy("The Office Gossip Show by Anmol Garg", ["Anmol Garg"])
    district = listing(
        "Office Chugli Standup Comedy Crowdwork Show",
        "The Comedy Theatre - Indiranagar, Bangalore",
        12.9700897,
        77.6393,
    )
    rows = [(e["url"], e | start) for e in (chugli, gossip, district)]
    events = run(tmp_path, rows)
    assert list(events) == [district["url"]]
    show = events[district["url"]]
    assert show["name"] == "Office Chugli Standup Comedy Crowdwork Show and 1 more"
    assert show["sameAs"] == [chugli["url"], gossip["url"]]


def test_dedup_merges_one_sites_renamed_listing(tmp_path):
    start = {"startDate": "2026-10-17T20:00:00+05:30"}
    a = comedy("Seriously Silly: Double Bill Comedy Show", ["Joteen Patro"])
    b = comedy("Seriously Silly: A Double Bill Comedy Show", ["Joteen Patro"])
    events = run(tmp_path, [(e["url"], e | start) for e in (a, b)])
    assert [e["name"] for e in events.values()] == [a["name"]]


def test_dedup_merges_one_show_listed_minutes_apart(tmp_path):
    venue = "My School Of Rock: Bengaluru"

    def mic(name, code, start):
        event = listing(name, venue, 12.93, 77.62) | {"startDate": start}
        return event | {"url": f"https://in.bookmyshow.com/events/{code}"}

    rows = [
        mic("Open Mic", "a", "2026-10-18T17:25:00+05:30"),
        mic("OPEN MIC - ROCK THE STAGE", "b", "2026-10-18T17:45:00+05:30"),
        mic("Open Mic", "c", "2026-10-18T19:00:00+05:30"),
        mic("Drum Circle", "d", "2026-10-18T17:30:00+05:30"),
    ]
    events = run(tmp_path, [(e["url"], e) for e in rows])
    assert sorted(u[-1] for u in events) == ["a", "c", "d"]
    assert events[rows[0]["url"]]["sameAs"] == [rows[1]["url"]]
