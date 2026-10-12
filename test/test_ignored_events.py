from src.processors import ignored_events
from src.processors.base import DROP


def test_listed_ids_are_dropped(monkeypatch):
    monkeypatch.setattr(ignored_events, "IGNORED_EVENT_UIDS", ["event_42414_0"])
    process = ignored_events.IgnoredEvents.process
    assert process("u", {"@id": "event_42414_0"}) == DROP
    assert process("u", {"@id": "event_42476_0"}) is None
    assert process("u", {}) is None
