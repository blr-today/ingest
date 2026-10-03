from processors.cost import Cost, tag


def test_tag_bands():
    assert [tag(a) for a in (0, 1, 499, 500, 1999, 2000)] == [
        "FREE", "BUDGET", "BUDGET", "VALUE", "VALUE", "PRICEY",
    ]


def test_cheapest_ticket_sets_the_tag():
    event = {"keywords": ["BAC"], "offers": [{"price": "2500"}, {"price": "₹1,499 onwards"}]}
    assert Cost.process("u", event)["keywords"] == ["BAC", "VALUE"]
