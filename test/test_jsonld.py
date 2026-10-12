from src.common.jsonld import JsonLdExtractor

EVENT = "test/fixtures/jsonld/event.html"
GRAPH = "test/fixtures/remote/graph.html"


def test_extracts_event_with_raw_control_characters():
    [event] = JsonLdExtractor().extract(open(EVENT).read())
    assert event["@type"] == "Event"
    assert event["name"] == "Bengaluru Boy by Danish Sait | Stand Up Comedy"
    assert event["startDate"] == "2026-10-25T12:00+5.5:00"


def test_extracts_graph_documents():
    items = JsonLdExtractor().extract(open(GRAPH, "rb").read())
    assert [list(i.keys()) for i in items] == [["@context", "@graph"]]
    assert "Event" in [x["@type"] for x in items[0]["@graph"]]


def test_lists_are_flattened_and_empty_items_dropped():
    html = (
        '<html><body><script type="application/ld+json">[{"@type": "Event"}, {}, {"@type": "Place"}]</script>'
        '<script type="application/ld+json">"just a string"</script>'
        '<script type="application/ld+json">{"@type": "Thing"}</script></body></html>'
    )
    assert JsonLdExtractor().extract(html) == [{"@type": "Event"}, {"@type": "Place"}, {"@type": "Thing"}]


def test_page_without_jsonld():
    assert JsonLdExtractor().extract("<html><body><p>Hi</p></body></html>") == []
