from types import SimpleNamespace

from common import eventbrite

PAGE = "test/fixtures/eventbrite/organizer.html"


def organizer(monkeypatch, content):
    seen = []

    def get(url):
        seen.append(url)
        return SimpleNamespace(content=content)
    monkeypatch.setattr(eventbrite, "get_cached_session", lambda: SimpleNamespace(get=get))
    return eventbrite.EB("68705192193"), seen


def test_links_come_from_next_data(monkeypatch):
    eb, seen = organizer(monkeypatch, open(PAGE, "rb").read())
    assert sorted(eb.fetch_links()) == [
        "https://www.eventbrite.com/e/deduction-deception-tickets-1988144242950",
        "https://www.eventbrite.com/e/international-board-gaming-weekend-tickets-1996773046935",
        "https://www.eventbrite.com/e/the-hsr-boardgame-social-tickets-1996773330784",
    ]
    assert seen == ["https://www.eventbrite.com/o/68705192193"]


def test_links_drop_query_and_duplicates(monkeypatch):
    html = open(PAGE).read().replace(
        '"url": "https://www.eventbrite.com/e/deduction-deception-tickets-1988144242950"',
        '"url": "https://www.eventbrite.co.uk/e/the-hsr-boardgame-social-tickets-1996773330784?aff=ebdsoporgprofile"',
    )
    eb, _ = organizer(monkeypatch, html.encode())
    assert sorted(eb.fetch_links()) == [
        "https://www.eventbrite.com/e/international-board-gaming-weekend-tickets-1996773046935",
        "https://www.eventbrite.com/e/the-hsr-boardgame-social-tickets-1996773330784",
    ]


def test_missing_next_data_gives_no_links(monkeypatch):
    eb, _ = organizer(monkeypatch, b"<html><body><p>No events</p></body></html>")
    assert eb.fetch_links() == []


def test_missing_upcoming_events_gives_no_links(monkeypatch):
    html = b'<script id="__NEXT_DATA__">{"props": {"pageProps": {"upcomingEvents": null}}}</script>'
    eb, _ = organizer(monkeypatch, html)
    assert eb.fetch_links() == []
