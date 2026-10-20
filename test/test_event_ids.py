import json
import sqlite3

from src.event_ids import assign_ids, namespace, upstream_key, write_ids


def ids(*events):
    return assign_ids([(e.pop("_url"), json.dumps(e)) for e in events])


def event(url, start="2026-10-24T11:00:00+05:30", **rest):
    return {"_url": url, "startDate": start, **rest}


def test_namespace_reverses_the_host_without_www():
    assert namespace("https://in.bookmyshow.com/events/x/ET1") == "com.bookmyshow.in"
    assert namespace("https://www.adidas.co.in/e/1") == "in.co.adidas"


def test_slug_suffix_ids():
    assert (
        upstream_key(
            "https://www.highape.com/bangalore/events/resin-jhumka-workshop-vv0tytlqlg",
            {},
        )
        == "vv0tytlqlg"
    )
    assert (
        upstream_key("https://www.skillboxes.com/events/bender2night-sbpwrmbz", {})
        == "sbpwrmbz"
    )
    assert (
        upstream_key("https://indiarunning.com/events/breakthrough_run_33370", {})
        == "33370"
    )


def test_json_ld_ids():
    assert (
        upstream_key(
            "https://iiwc.in/event/x/", {"@id": "2732-1792454400-1792972799@iiwc.in"}
        )
        == "2732"
    )
    assert (
        upstream_key(
            "https://blrbirders.com/events/x", {"@id": "com.blrbirders:event_666_24"}
        )
        == "666"
    )
    assert (
        upstream_key("https://courtyardkoota.com/events/x/", {"@id": "event_42414_0"})
        == "42414"
    )
    assert (
        upstream_key(
            "https://map-india.org/map-events/x/", {"@id": "1427@map-india.org"}
        )
        == "1427"
    )
    # A URL @id says nothing the event URL does not
    assert (
        upstream_key(
            "https://underline.center/t/x/841",
            {"@id": "https://www.district.in/events/x#event"},
        )
        == "841"
    )


def test_query_and_fragment_ids():
    assert (
        upstream_key("https://attagalatta.com/event_page.php?eventid=EVT2145", {})
        == "EVT2145"
    )
    assert upstream_key("https://cksl.in/?eid=00pag#section3", {}) == "00pag"
    assert upstream_key("https://www.deardk.com/?ref=blr.today", {}) == ""
    assert (
        upstream_key("https://lavonne.in/courses/weekend-classes#class-ags71gv9", {})
        == "ags71gv9"
    )
    assert (
        upstream_key("https://rangashankara.org/book-tickets-2/#20261023-1930", {})
        == "book-tickets-2"
    )
    assert (
        upstream_key("https://www.district.in/events/garba-oct23-2026-buy-tickets", {})
        == "garba-oct23-2026"
    )


def test_start_time_only_for_repeats():
    once, *twice = ids(
        event("https://puttingscene.com/events/GS7JAK"),
        event("https://puttingscene.com/events/WTSMSE", "2026-10-03T08:00:00+05:30"),
        event("https://puttingscene.com/events/WTSMSE", "2026-10-03T09:00:00+05:30"),
    )
    assert once == "com.puttingscene.gs7jak"
    assert twice == [
        "com.puttingscene.wtsmse.20261003t0800",
        "com.puttingscene.wtsmse.20261003t0900",
    ]


def test_venue_splits_one_slot_in_many_places():
    url = "https://in.bookmyshow.com/events/bedazzle/ET00510747"
    assert ids(
        event(url, location={"name": "URU Whitefield: Bengaluru"}),
        event(url, location=[{"name": "Tim Hortons, HSR Layout: Bengaluru."}]),
    ) == [
        "com.bookmyshow.in.et00510747.20261024t1100.uru-whitefield",
        "com.bookmyshow.in.et00510747.20261024t1100.tim-hortons-hsr-layout",
    ]


def test_counter_follows_content_not_row_order():
    a = event("https://example.com/e/x", name="A")
    b = event("https://example.com/e/x", name="B")
    first = ids(dict(a), dict(b))
    assert ids(dict(b), dict(a)) == first[::-1]
    assert sorted(first) == [
        "com.example.x.20261024t1100",
        "com.example.x.20261024t1100-2",
    ]


def test_ids_are_url_safe():
    [i] = ids(event("https://allevents.in/bangalore/just-₹49/", name="x"))
    assert i == "in.allevents.just-49"
    [i] = ids(event("https://www.deardk.com/?ref=blr.today"))
    assert i == "com.deardk.event"


def test_source_identifier_is_the_id():
    form = "https://docs.google.com/forms/d/e/abc/viewform"
    assert ids(event(form, identifier="gcw.2026-11-01")) == ["gcw.2026-11-01"]
    assert ids(event(form, identifier="")) == ["com.google.docs.viewform"]
    a, b = event(form, identifier="gcw.x"), event(form, identifier="gcw.x", start="2026-10-25")
    assert ids(a, b) == ["gcw.x.20261024t1100", "gcw.x.20261025"]


def test_write_ids_adds_the_column(tmp_path):
    db = tmp_path / "events.db"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE events (url TEXT, event_json TEXT)")
        conn.execute(
            "INSERT INTO events VALUES (?, ?)",
            ("https://sofarsounds.com/events/67871", "{}"),
        )
    write_ids(db)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT id FROM events").fetchall() == [
            ("com.sofarsounds.67871",)
        ]
