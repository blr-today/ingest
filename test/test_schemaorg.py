from src.common.schemaorg import TYPES


def test_event_types_are_unique_schema_names():
    assert len(TYPES) == len(set(TYPES))
    assert "Event" in TYPES and "ScreeningEvent" in TYPES
    assert all(t[0].isupper() and " " not in t for t in TYPES)
