import townscript
from townscript import get_event_urls, main

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


def test_main_skips_other_cities(monkeypatch, capsys):
    def urls(org_id):
        yield f"https://www.townscript.com/e/{org_id}-bangalore"
        yield f"https://www.townscript.com/e/{org_id}-pune"

    monkeypatch.setattr(townscript, "get_event_urls", urls)
    main()
    lines = capsys.readouterr().out.splitlines()
    assert "https://www.townscript.com/e/5378763-bangalore" in lines
    assert "https://www.townscript.com/e/1306109-bangalore" in lines
    assert not any(line.endswith("-pune") for line in lines)
