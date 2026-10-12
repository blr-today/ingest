from src.processors.highape import HighApe


def offers(*prices):
    return [
        {"@type": "Offer", "name": n, "price": p, "priceCurrency": "INR"}
        for n, p in prices
    ]


def test_hidden_free_entry_is_dropped():
    event = {"offers": offers(("Stag", "999"), ("Entry", "0"))}
    assert HighApe.process("u", event)["offers"] == offers(("Stag", "999"))


def test_real_offers_are_kept():
    for event in (
        {"offers": offers(("Entry", "0"), ("Stag", "999"))},
        {"offers": offers(("Entry", "499"))},
        {"offers": offers(("Guestlist", "0"))},
    ):
        assert HighApe.process("u", dict(event)) == event


def test_missing_offers():
    assert HighApe.process("u", {"name": "x"}) == {"name": "x"}
    assert HighApe.process("u", {"offers": []}) == {"offers": []}


def test_odd_offers_are_kept():
    for event in ({"offers": "Free"}, {"offers": None}, {"offers": ["Entry"]}):
        assert HighApe.process("u", dict(event)) == event
