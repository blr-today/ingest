import datetime
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

import atta_galatta
from atta_galatta import fetch_events, links_out, make_event, ticket_link

FIXTURES = Path(__file__).parent / "fixtures" / "atta_galatta"


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def json(self):
        return json.loads(self.text)


class FakeSession:
    def __init__(self, **overrides):
        self.overrides = overrides

    def get(self, url):
        if url.endswith("/events.php"):
            return FakeResponse((FIXTURES / "events.json").read_text())
        event_id = url.split("eventid=")[1]
        return FakeResponse(self.overrides.get(event_id) or (FIXTURES / f"{event_id}.html").read_text())


@pytest.fixture
def site(monkeypatch):
    class FrozenDatetime(datetime.datetime):
        @classmethod
        def today(cls):
            return cls(2026, 10, 3)

    monkeypatch.setattr(atta_galatta, "datetime", SimpleNamespace(datetime=FrozenDatetime))
    monkeypatch.setattr(atta_galatta, "session", FakeSession())
    return {e["eventid"]: e for e in fetch_events()}


def page(event_id):
    return BeautifulSoup((FIXTURES / f"{event_id}.html").read_text(), "html.parser")


def test_fetch_events_skips_past_dates(site):
    assert list(site) == ["EVT2170", "EVT2171", "EVT2086", "EVT2166"]
    assert site["EVT2170"]["date"].isoformat() == "2026-10-04T00:00:00+05:30"


def test_ticket_link_must_match_the_title():
    assert ticket_link(page("EVT2170"), "Kahaani Play-Ground - A Text-Based Theatre Workshop") == "https://urbanaut.app/spot/kahaani-play-ground-a-text-based-theatre-workshop"
    assert ticket_link(page("EVT2171"), "Lahe Lahe Caravan presents Harry Potter Book Discussion") is None
    assert ticket_link(page("EVT2166"), "Alcohol Use and Youth") is None


def test_walk_in_events_do_not_link_out():
    assert links_out(page("EVT2170"))
    assert not links_out(page("EVT2166"))
    assert not links_out(BeautifulSoup("<a id='registerbtn' href='https://attagalatta.com/rsvp'>RSVP</a>", "html.parser"))
    assert not links_out(BeautifulSoup("<p>No button</p>", "html.parser"))


def test_ticketed_workshop(site):
    event = make_event(site["EVT2170"])
    assert event["name"] == "Kahaani Play-Ground - A Text-Based Theatre Workshop"
    assert event["@type"] == "EducationEvent"
    assert event["performer"] == "Parwana Theatre"
    assert event["keywords"] == ["Theatre", "Workshop"]
    assert event["startDate"] == "2026-10-04T09:30:00+05:30"
    assert event["endDate"] == "2026-10-04T13:30:00+05:30"
    assert event["sameAs"] == "https://urbanaut.app/spot/kahaani-play-ground-a-text-based-theatre-workshop"
    assert event["description"].startswith("An intensive one-day workshop")
    assert event["image"] == "https://attagalatta.com/admin/uploads/events/855574402.png"
    assert "offers" not in event


def test_book_events_are_literary(site):
    discussion = make_event(site["EVT2171"])
    assert discussion["@type"] == "LiteraryEvent"
    assert "sameAs" not in discussion
    launch = make_event(site["EVT2086"])
    assert launch["@type"] == "LiteraryEvent"
    assert launch["sameAs"] == "https://urbanaut.app/spot/we-matched-unfortunately"


def test_walk_in_event_is_free(site):
    event = make_event(site["EVT2166"])
    assert event["keywords"] == []
    assert event["@type"] == "LiteraryEvent"
    assert event["isAccessibleForFree"] is True
    assert event["offers"] == [{"@type": "Offer", "price": "0", "priceCurrency": "INR", "url": "https://attagalatta.com/event_page.php?eventid=EVT2166"}]


@pytest.mark.parametrize("subtitle, keywords, expected", [
    ("Theatre Performance", "Theatre | Play", "TheaterEvent"),
    ("Music Performance", "Concert", "MusicEvent"),
    ("For Children", "Storytelling", "ChildrensEvent"),
    ("Film Club", "Film | Screening", "ScreeningEvent"),
    ("An evening chat", "Mental Health | Discussion", "SocialEvent"),
    ("Mixer", "Social", "SocialEvent"),
    ("Poems", "Poetry", "LiteraryEvent"),
    ("Talk", "Science", "LiteraryEvent"),
])
def test_event_type_from_subtitle_and_keywords(site, monkeypatch, subtitle, keywords, expected):
    html = (FIXTURES / "EVT2170.html").read_text()
    html = html.replace("A Text-Based Theatre Workshop ", subtitle).replace("Theatre </b></a>| ", "").replace(">Workshop</a>", f">{keywords}</a>")
    monkeypatch.setattr(atta_galatta, "session", FakeSession(EVT2170=html))
    assert make_event(site["EVT2170"])["@type"] == expected


def test_missing_times_and_description(site, monkeypatch):
    html = (FIXTURES / "EVT2170.html").read_text()
    soup = BeautifulSoup(html, "html.parser")
    soup.select_one("#product-content").string = ""
    soup.select_one("#after-title a").string = "TBA - TBA"
    monkeypatch.setattr(atta_galatta, "session", FakeSession(EVT2170=str(soup)))
    event = make_event(dict(site["EVT2170"], eventstarttime="TBA"))
    assert event["description"] == site["EVT2170"]["description"]
    assert "startDate" not in event
    assert "endDate" not in event
