import datetime
from pathlib import Path
from types import SimpleNamespace

from src.sources import fillum

FIXTURES = Path(__file__).parent / "fixtures/fillum"
HOST = "https://fillum.in/user/52"
SCREENING = "https://fillum.in/screening/6345"
TICKET = "https://fillum.in/p/448"
PAGES = {
    HOST: "host.html",
    SCREENING: "screening-6345.html",
    "https://fillum.in/screening/6226": "screening-6226.html",
    TICKET: "ticket-448.html",
    "https://fillum.in/p/426": "ticket-426.html",
}
EVENT = {
    "@context": "https://schema.org",
    "@type": "ScreeningEvent",
    "name": "Sleepaway Camp (1983)",
    "url": SCREENING,
    "startDate": "2026-10-17T18:00:00+05:30",
    "image": "https://fillum.in/images/filmbg/3557-tn.jpg",
    "description": "Years after a terrible boating accident, Angela is sent to Camp Arawak where a series "
    'of bizarre and violent "accidents" begin to claim the lives of various campers.'
    "\n\nThe screening will be followed by a conversation.",
    "location": {
        "@type": "Place",
        "name": "Untitled Arts Foundation",
        "address": "Untitled Arts Foundation, Bangalore",
    },
    "organizer": {"@type": "Organization", "name": "Bangalore Film Forum", "url": HOST},
    "workPresented": {
        "@type": "Movie",
        "name": "Sleepaway Camp",
        "director": {"@type": "Person", "name": "Robert Hiltzik"},
    },
    "offers": {
        "@type": "Offer",
        "price": 200,
        "priceCurrency": "INR",
        "url": TICKET,
        "availability": "https://schema.org/InStock",
    },
}


def serve(monkeypatch, *edits, now=(2026, 1, 1)):
    pages = {url: (FIXTURES / name).read_text() for url, name in PAGES.items()}
    for url, old, new in edits:
        assert old in pages[url]
        pages[url] = pages[url].replace(old, new, 1)
    fetched = []

    def get(url, headers=None, timeout=None):
        assert headers == fillum.USER_AGENT_HEADERS and timeout == 30
        fetched.append(url)
        return SimpleNamespace(text=pages[url])

    class Fixed(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(*now, tzinfo=tz)

    monkeypatch.setattr(fillum, "datetime", SimpleNamespace(datetime=Fixed))
    monkeypatch.setattr(fillum, "get_cached_session", lambda: SimpleNamespace(get=get))
    return fetched


def test_host_page_yields_upcoming_screening(monkeypatch):
    fetched = serve(monkeypatch)
    assert fillum.events() == [EVENT]
    assert fetched == [HOST, SCREENING, TICKET]


def test_past_screening_is_skipped(monkeypatch, capsys):
    fetched = serve(monkeypatch, now=(2026, 10, 18))
    assert fillum.events() == []
    assert fetched == [HOST]
    assert f"[FILLUM] Event in past: {SCREENING}" in capsys.readouterr().out


def test_other_city_is_skipped(monkeypatch, capsys):
    card = 'gscreeningbox screeningcity screeningcitybangalore'
    fetched = serve(monkeypatch, (HOST, card, card.replace("bangalore", "delhi")))
    assert fillum.events() == []
    assert fetched == [HOST]
    assert f"[FILLUM] Not in Bangalore: {SCREENING}" in capsys.readouterr().out


def test_closed_tickets_give_no_offer(monkeypatch, capsys):
    serve(monkeypatch, (SCREENING, 'href="p/448"', 'href="p/426"'))
    [event] = fillum.events()
    assert "offers" not in event
    assert "[FILLUM] No tickets on sale: https://fillum.in/p/426" in capsys.readouterr().out


def test_no_ticket_button_gives_no_offer(monkeypatch):
    button = '<a href="p/448" class="ticketbtn btn btn-default btn-xs">Buy Tickets</a>'
    fetched = serve(monkeypatch, (SCREENING, button, ""))
    [event] = fillum.events()
    assert event == {k: v for k, v in EVENT.items() if k != "offers"}
    assert fetched == [HOST, SCREENING]


def test_missing_director_is_omitted(monkeypatch):
    serve(monkeypatch, (SCREENING, "<br><i>Robert Hiltzik</i>", ""))
    [event] = fillum.events()
    assert "director" not in event["workPresented"]


def test_decimal_price_is_kept(monkeypatch):
    serve(monkeypatch, (TICKET, 'name="productprice" value="200"', 'name="productprice" value="199.50"'))
    [event] = fillum.events()
    assert event["offers"]["price"] == 199.5
