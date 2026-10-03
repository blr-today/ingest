from src.sources.puttingscene import make_events, make_offers


def tier(**kw):
    return {"name": "Regular", "price": {"amount_in_minor_units": 99900}, **kw}


def test_open_tier_counts_seats():
    [offer] = make_offers({"ticket_tiers": [tier(is_sold_out=False, available_capacity=6)]})
    assert offer["availability"] == "https://schema.org/InStock"
    assert offer["remainingAttendeeCapacity"] == 6


def test_closed_tier_drops_unsold_seats():
    [offer] = make_offers({"ticket_tiers": [tier(is_sold_out=True, available_capacity=2)]})
    assert offer["availability"] == "https://schema.org/SoldOut"
    assert "remainingAttendeeCapacity" not in offer


def test_empty_tier_is_sold_out():
    [offer] = make_offers({"ticket_tiers": [tier(available_capacity=0)]})
    assert offer["availability"] == "https://schema.org/SoldOut"
    assert "remainingAttendeeCapacity" not in offer


def test_slot_capacity_is_the_total():
    event = {"id": "E1", "title": "Workshop", "is_paid": True, "slots": [
        {"start_at": "2026-10-10T18:00:00+05:30", "max_attendees": 6, "ticket_tiers": [tier(available_capacity=6)]},
        {"start_at": "2026-10-17T18:00:00+05:30", "ticket_tiers": [tier(available_capacity=6)]},
    ]}
    first, second = make_events(event)
    assert first["maximumAttendeeCapacity"] == 6
    assert "maximumAttendeeCapacity" not in second
