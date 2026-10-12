from src.sources import townscript
from src.sources.townscript import get_event_urls, urls

# The listing endpoint now 404s; names come from cached townscript.com/e/ pages
LISTING = {
    "data": [
        {"shortName": "broke-bibliophiles-bangalore-meetup-88-204322"},
        {"shortName": "broke-bibliophiles-bangalore-meetup-87-221321"},
    ]
}


class FakeFetch:
    urls = []

    def __init__(self, cache=None):
        assert cache == {"serializer": "json"}

    def get(self, url):
        FakeFetch.urls.append(url)
        return type("R", (), {"json": lambda self: LISTING})()


def test_event_urls(monkeypatch):
    monkeypatch.setattr(townscript, "Fetch", FakeFetch)
    assert list(get_event_urls("1306109")) == [
        "https://www.townscript.com/e/broke-bibliophiles-bangalore-meetup-88-204322",
        "https://www.townscript.com/e/broke-bibliophiles-bangalore-meetup-87-221321",
    ]
    assert FakeFetch.urls[-1] == "https://www.townscript.com/listings/event/upcoming/userId/1306109"


def org_urls(org_id):
    yield f"https://www.townscript.com/e/{org_id}-bangalore"
    yield f"https://www.townscript.com/e/{org_id}-pune"


def test_urls_skip_other_cities(monkeypatch):
    monkeypatch.setattr(townscript, "get_event_urls", org_urls)
    lines = urls()
    assert "https://www.townscript.com/e/5378763-bangalore" in lines
    assert "https://www.townscript.com/e/1306109-bangalore" in lines
    assert not any(line.endswith("-pune") for line in lines)


def test_events_fetch_unique_sorted_urls(monkeypatch):
    monkeypatch.setattr(townscript, "urls", lambda: ["https://t.com/e/b", "https://t.com/e/a", "https://t.com/e/b"])
    monkeypatch.setattr(townscript, "events_from_urls", lambda urls: [{"url": u} for u in urls])
    assert townscript.events() == [{"url": "https://t.com/e/a"}, {"url": "https://t.com/e/b"}]
