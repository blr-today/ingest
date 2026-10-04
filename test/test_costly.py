from processors.base import DROP
from processors.costly import Costly


def table(*prices):
    return {"offers": [{"price": p, "priceCurrency": "INR"} for p in prices]}


def test_only_table_tickets_are_dropped():
    assert Costly.process("u", table("52500.00", "105000.00")) == DROP


def test_one_regular_ticket_keeps_the_event():
    assert Costly.process("u", table("1999.00", "52500.00")) is None


def test_limit_itself_is_kept():
    assert Costly.process("u", table("15000")) is None


def test_unpriced_or_foreign_events_are_kept():
    assert Costly.process("u", {}) is None
    assert Costly.process("u", {"offers": {"price": "20000", "priceCurrency": "USD"}}) is None
