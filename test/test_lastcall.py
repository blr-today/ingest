import json
import sqlite3

from processors.lastcall import LastCall, slot_totals


def tags(event):
    return LastCall.process("u", event).get("keywords")


def test_event_count():
    assert tags({"keywords": ["X"], "remainingAttendeeCapacity": "8"}) == ["X", "LASTCALL"]
    assert tags({"keywords": [], "remainingAttendeeCapacity": 9}) == []
    assert tags({"keywords": [], "remainingAttendeeCapacity": 0}) == []


def test_known_capacity_uses_a_tenth():
    assert tags({"keywords": [], "remainingAttendeeCapacity": 20, "maximumAttendeeCapacity": 200}) == ["LASTCALL"]
    assert tags({"keywords": [], "remainingAttendeeCapacity": 21, "maximumAttendeeCapacity": 200}) == []
    assert tags({"keywords": [], "remainingAttendeeCapacity": 8, "maximumAttendeeCapacity": 20}) == []
    assert tags({"keywords": [], "remainingAttendeeCapacity": 2, "maximumAttendeeCapacity": 20}) == ["LASTCALL"]


def test_mid_capacity_uses_a_quarter_up_to_the_limit():
    assert tags({"keywords": [], "remainingAttendeeCapacity": 8, "maximumAttendeeCapacity": 45}) == ["LASTCALL"]
    assert tags({"keywords": [], "remainingAttendeeCapacity": 9, "maximumAttendeeCapacity": 45}) == []
    assert tags({"keywords": [], "remainingAttendeeCapacity": 3, "maximumAttendeeCapacity": 15}) == ["LASTCALL"]
    assert tags({"keywords": [], "remainingAttendeeCapacity": 4, "maximumAttendeeCapacity": 15}) == []


def test_small_capacity_rounds_up():
    assert tags({"keywords": [], "remainingAttendeeCapacity": 1, "maximumAttendeeCapacity": 6}) == ["LASTCALL"]
    assert tags({"keywords": [], "remainingAttendeeCapacity": 2, "maximumAttendeeCapacity": 6}) == []


def test_slots_add_up():
    offers = [{"remainingAttendeeCapacity": 5}, {"remainingAttendeeCapacity": 3}]
    assert tags({"keywords": [], "offers": offers}) == ["LASTCALL"]
    offers.append({"inventoryLevel": 1})
    assert tags({"keywords": [], "offers": offers}) == []


def test_sold_out_tiers_count_as_zero():
    offers = [{"availability": "SoldOut"}, {"inventoryLevel": 2}]
    assert tags({"keywords": [], "offers": offers}) == ["LASTCALL"]


def test_sold_out_tiers_ignore_their_count():
    offers = [{"availability": "https://schema.org/SoldOut", "remainingAttendeeCapacity": 2},
              {"availability": "https://schema.org/InStock", "remainingAttendeeCapacity": 7}]
    assert tags({"keywords": [], "offers": offers}) == ["LASTCALL"]
    offers[1]["remainingAttendeeCapacity"] = 8
    assert tags({"keywords": [], "offers": offers}) == ["LASTCALL"]
    offers[1]["remainingAttendeeCapacity"] = 9
    assert tags({"keywords": [], "offers": offers}) == []


def test_uncounted_tier_is_unknown():
    offers = [{"inventoryLevel": 2}, {"price": "500"}]
    assert tags({"keywords": [], "offers": offers}) == []


def test_slots_of_one_listing_add_up(tmp_path):
    db = tmp_path / "events.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE events (url TEXT, event_json TEXT)")
    rows = [
        ("https://a/x", {"remainingAttendeeCapacity": 6}),
        ("https://a/x", {"remainingAttendeeCapacity": 6}),
        ("https://u/y#2026-10-01T1900", {"remainingAttendeeCapacity": 3, "maximumAttendeeCapacity": 40}),
        ("https://u/y#2026-10-08T1900", {"remainingAttendeeCapacity": 4, "maximumAttendeeCapacity": 40}),
        ("https://u/z#1", {"remainingAttendeeCapacity": 2}),
        ("https://u/z#2", {"offers": [{"price": "100"}]}),
    ]
    conn.executemany("INSERT INTO events VALUES (?, ?)", [(u, json.dumps(e)) for u, e in rows])
    conn.commit()
    assert slot_totals(str(db)) == {"https://a/x": (12, None), "https://u/y": (7, 80), "https://u/z": (None, None)}
