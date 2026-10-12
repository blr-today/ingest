from pathlib import Path
from types import SimpleNamespace

from src.sources import lavonne
from src.sources.lavonne import URL, fetch_classes, make_event, parse_time_range

HTML = (Path(__file__).parent / "fixtures/lavonne/weekend-classes.html").read_text()


def test_parse_time_range():
    start, end = parse_time_range("10:00 am to 1:30 pm", "2026-09-26")
    assert start.isoformat() == "2026-09-26T10:00:00+05:30"
    assert end.isoformat() == "2026-09-26T13:30:00+05:30"


def test_fetch_classes_reads_split_rsc_payload():
    classes = fetch_classes(HTML)
    assert [c["title"] for c in classes][:2] == ["Enriched Breads", "Cupcakes, Cookies & Muffins"]
    assert [c["location"] for c in classes] == ["Bangalore", "Delhi", "Bangalore", "Bangalore"]


def test_sold_out_class():
    event = make_event(fetch_classes(HTML)[0])
    assert event["name"] == "Enriched Breads"
    assert event["startDate"] == "2026-09-26T09:00:00+05:30"
    assert event["endDate"] == "2026-09-26T17:00:00+05:30"
    assert event["offers"]["price"] == "4500"
    assert event["offers"]["availability"] == "https://schema.org/SoldOut"
    assert "remainingAttendeeCapacity" not in event["offers"]
    assert event["description"].endswith("Mascarpone-filled Brioche")
    assert event["url"] == f"{URL}#class-oqdj3ovqpnnetfpuhic7xeit"


def test_class_with_seats_left():
    offer = make_event(fetch_classes(HTML)[2])["offers"]
    assert offer["availability"] == "https://schema.org/InStock"
    assert offer["remainingAttendeeCapacity"] == 16


def test_events_keep_bangalore_classes(monkeypatch):
    session = SimpleNamespace(get=lambda url: SimpleNamespace(text=HTML))
    monkeypatch.setattr(lavonne, "get_cached_session", lambda: session)
    events = lavonne.events()
    assert len(events) == 3
    assert all(e["location"]["name"] == "Lavonne Academy" for e in events)
