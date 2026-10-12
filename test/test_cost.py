from processors.cost import Cost, as_keywords, flatten, price, tag


def test_tag_bands():
    assert [tag(a) for a in (0, 1, 499, 500, 1999, 2000)] == [
        "FREE", "BUDGET", "BUDGET", None, None, "PRICEY",
    ]


def test_cheapest_ticket_sets_the_tag():
    event = {"keywords": ["BAC"], "offers": [{"price": "2500"}, {"price": "₹1,499 onwards"}]}
    assert Cost.process("u", event)["keywords"] == ["BAC"]


def test_mid_price_drops_an_old_tag():
    event = {"keywords": ["BUDGET"], "offers": [{"price": "999"}]}
    assert Cost.process("u", event)["keywords"] == []


def test_price_formats():
    values = (0, 250.5, "Free", " FREE ", "Rs. 1,200/-", "TBA", True, None)
    assert [price({"price": v}) for v in values] == [
        0.0, 250.5, 0.0, 0.0, 1200.0, None, None, None,
    ]
    assert price({"lowPrice": "799"}) == 799.0


def test_flatten_aggregate_offers():
    aggregate = {"@type": "AggregateOffer", "offers": [{"price": 1}, [{"price": 2}]]}
    offers = list(flatten([aggregate, {"price": 3}, "x"]))
    assert offers == [{"price": 1}, {"price": 2}, {"price": 3}]
    assert list(flatten({"@type": "AggregateOffer", "offerCount": "0", "price": 0})) == []


def test_as_keywords():
    assert as_keywords({"content": "Comedy , All,"}) == ["Comedy", "All"]
    assert as_keywords("A,B") == ["A", "B"]
    assert as_keywords(["A"]) == ["A"]
    assert as_keywords(None) == []


def test_free_events():
    assert Cost.process("u", {"offers": {"price": "0"}})["keywords"] == ["FREE"]
    event = {"isAccessibleForFree": "true", "keywords": "X"}
    assert Cost.process("u", event)["keywords"] == ["X", "FREE"]


def test_couple_passes_and_foreign_prices_are_ignored():
    event = {"offers": [{"name": "Couple Entry", "price": "0"}, {"price": "2500"}]}
    assert Cost.process("u", event)["keywords"] == ["PRICEY"]
    event = {"keywords": ["X"], "offers": [{"price": "20", "priceCurrency": "USD"}]}
    assert Cost.process("u", event) == {"keywords": ["X"], "offers": event["offers"]}


def test_unpriced_events_are_untouched():
    event = {"keywords": ["FREE"], "offers": [{"price": "TBA"}]}
    assert Cost.process("u", event)["keywords"] == ["FREE"]
