from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

import bbb

FEED = Path(__file__).parent / "fixtures" / "bbb" / "feed.xml"
MAP = "https://maps.app.goo.gl/eDix9xKSoYUNqFUu5"
RSVP = "https://forms.gle/Cd3joYXt9jvN19Ma9"


class FakeResponse:
    def __init__(self, content=b"", status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}


class FakeSession:
    def __init__(self, redirects=None):
        self.redirects = redirects or {}

    def get(self, url, allow_redirects=True, timeout=None):
        if url == bbb.FEED:
            return FakeResponse(FEED.read_bytes())
        if url in self.redirects:
            return FakeResponse(status_code=302, headers={"location": self.redirects[url]})
        return FakeResponse()


class FakeClient:
    def __init__(self, nouls, choices):
        self.nouls, self.choices = nouls, choices

    def system_one(self, state, questions):
        self.state, self.questions = state, questions
        return SimpleNamespace(
            nouls={k: SimpleNamespace(noul=v) for k, v in self.nouls.items()},
            choices={k: SimpleNamespace(choice=c, confidence=0.9) for k, c in self.choices.items()},
        )


@pytest.fixture
def posts():
    return list(bbb.read_posts(FakeSession()))


def picks(**kw):
    return {k: (v, 0.9) for k, v in kw.items()}


def test_feed_reads_latest_posts_only(posts):
    assert [p["title"] for p in posts] == ["BBB Meetup #100 🎉", "Broke Bibliophiles Bangalore Bulletin #32.5"]
    assert posts[0]["url"] == "https://brokebibliophilesbangalore.substack.com/p/bbb-meetup-100"
    assert posts[0]["published"] == date(2026, 10, 4)
    assert posts[0]["image"] is None


def test_post_text_and_hints(posts):
    post = posts[0]
    assert post["text"].startswith("Well, we’ve somehow made it to 100 meetups.")
    assert "Thanks for reading" not in post["text"]
    assert "Samagata Foundation" in post["bold"]
    assert "Samagata Foundation" in post["segments"]
    assert "250" in post["amounts"]
    assert set(post["links"]) == {MAP, RSVP, "https://www.instagram.com/brokebibliophilesbangalore"}
    assert post["maps"] == [MAP]


def test_short_links_count_as_maps(posts):
    assert posts[1]["maps"] == ["https://goo.gl/maps/i2GTZAmU42ZQQ4GW6"]
    assert "The Bookworm, Church Street" in posts[1]["segments"]


def test_segments_strip_labels_and_emoji():
    assert bbb.segments(["📍 Venue: Samagata Foundation\n🕑 Date and Time: 11th October"]) == [
        "Samagata Foundation",
        "11th October",
    ]
    assert bbb.segments(["As always, Atta Galatta - https://x.y/z"]) == ["Atta Galatta"]


def test_amounts_skip_small_and_large_numbers():
    assert bbb.amounts("Pay INR 250 or 1,200 on the 11th at 6:00 PM, 10,000 seats") == ["250", "1,200"]


def test_resolve_follows_redirects_and_consent():
    session = FakeSession({
        "https://goo.gl/a": "https://example.com/b?utm_source=x",
        "https://maps.app.goo.gl/c": "https://consent.google.com/m?continue=https://www.google.com/maps/place/X",
    })
    assert bbb.resolve(session, "https://goo.gl/a") == "https://example.com/b"
    assert bbb.resolve(session, "https://maps.app.goo.gl/c") == "https://www.google.com/maps/place/X"


def test_event_date_rolls_year_forward():
    assert bbb.event_date(picks(month="10", day="11"), date(2026, 10, 4)) == date(2026, 10, 11)
    assert bbb.event_date(picks(month="1", day="18"), date(2026, 10, 4)) == date(2027, 1, 18)
    assert bbb.event_date(picks(month="1", day="18", year="2026"), date(2026, 10, 4)) == date(2026, 1, 18)
    assert bbb.event_date(picks(month="none", day="18"), date(2026, 10, 4)) is None


def test_name_adds_club_prefix():
    assert bbb.name("Meetup #100") == "Broke Bibliophiles Bangalore: Meetup #100"
    assert bbb.name("Broke Bibliophiles Bangalore #100") == "Broke Bibliophiles Bangalore #100"


def test_place_resolves_single_map(posts, monkeypatch):
    monkeypatch.setattr(bbb.maps, "resolve", lambda link: ("Samagata, Bengaluru", 12.9, 77.6))
    location = bbb.place(posts[0], picks(venue="Samagata Foundation"))
    assert location["address"] == "Samagata, Bengaluru"
    assert location["geo"]["latitude"] == 12.9
    assert location["hasMap"] == MAP
    assert bbb.place(posts[0], picks(venue="none")) is None


def test_place_without_map(posts, monkeypatch):
    post = dict(posts[0], maps=[])
    location = bbb.place(post, picks(venue="Samagata Foundation"))
    assert location == {"@type": "Place", "name": "Samagata Foundation", "address": "Samagata Foundation, Bengaluru"}


def test_ask_builds_questions_from_post(posts):
    client = FakeClient({"event": 0.9, "has_fee": 0.8, "has_end": 0.9}, {"month": "10", "fee": "250"})
    nouls, answers = bbb.ask(client, posts[0])
    assert nouls["event"] == 0.9
    assert answers["fee"] == ("250", 0.9)
    assert client.state["title"] == "BBB Meetup #100 🎉"
    assert set(client.questions["rsvp"].criteria) == {RSVP, "https://www.instagram.com/brokebibliophilesbangalore", "none"}
    assert "map" not in client.questions


def test_to_event_from_answers(posts, monkeypatch):
    monkeypatch.setattr(bbb.maps, "resolve", lambda link: None)
    answers = picks(month="10", day="11", name="Broke Bibliophiles Bangalore #100", venue="Samagata Foundation",
                    fee="250", rsvp=RSVP, start_hour="14", end_hour="18")
    event = bbb.to_event(posts[0], {"has_fee": 0.9, "has_end": 0.9}, answers)
    assert event["name"] == "Broke Bibliophiles Bangalore #100"
    assert event["startDate"] == "2026-10-11T14:00:00+05:30"
    assert event["endDate"] == "2026-10-11T18:00:00+05:30"
    assert event["offers"] == {"@type": "Offer", "price": "250", "priceCurrency": "INR", "url": RSVP}
    assert event["location"]["hasMap"] == MAP
    assert "image" not in event


def test_to_event_without_time_or_fee(posts):
    event = bbb.to_event(dict(posts[0], image="https://img"), {"has_fee": 0.1}, picks(month="10", day="11", fee="250"))
    assert event["startDate"] == "2026-10-11"
    assert event["name"] == "Broke Bibliophiles Bangalore: BBB Meetup #100 🎉"
    assert event["image"] == "https://img"
    assert "offers" not in event and "endDate" not in event and "location" not in event
    assert bbb.to_event(posts[0], {}, picks(day="11")) is None
