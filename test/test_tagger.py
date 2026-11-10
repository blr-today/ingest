import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from typesafe_sdk import TypeSafeError

from src import tagger
from src.common.activities import EXCLUDE, QUESTIONS, TAGS, THRESHOLDS, VERSION, with_parents
from src.tagger import (
    RULES,
    ask,
    by_jev,
    by_rules,
    event_tags,
    jev_tags,
    jev_type,
    keywords,
    state,
)

ROWS = json.loads((Path(__file__).parent / "fixtures/tagger/events.json").read_text())
# Canned Jev replies by event name; a missing name fails the call
REPLIES = {
    "Japanese Kintsugi ": (
        {"ART-CRAFT/KINTSUGI": 0.9, "ART-CRAFT": 0.8, "ART-CRAFT/POTTERY": 0.6},
        "EducationEvent",
        0.8,
    ),
    "Horn OK Quiz | India-Themed Trivia Game Show by Tasty Trivia": (
        {"GAMES/QUIZ": 0.95, "EXPO": 0.7},
        "SocialEvent",
        0.4,
    ),
    "Japanese Kintsugi": ({"ART-CRAFT/KINTSUGI": 0.95}, "VisualArtsEvent", 0.9),
}


def tags(name, type_="Event", keywords=()):
    return by_rules({"@type": type_, "name": name, "keywords": list(keywords)})


def test_sports_screenings():
    assert "SPORTS-SCREENING/F1" in tags("F1 Singapore Grand Prix | Live Screening | Watson's")
    assert "SPORTS-SCREENING/CRICKET" in tags("Screening of India vs West Indies | The Studs")
    assert not tags("BENGALURU RUN by KAR IES") & {"SPORTS-SCREENING/F1", "SPORTS-SCREENING"}


def test_movie_screening_skips_sports():
    assert "MOVIE-SCREENING" in tags("Screening of Eat Pray Love", "ScreeningEvent")
    assert "MOVIE-SCREENING" not in tags(
        "F1 Italy Grand Prix | Live Screening", "ScreeningEvent"
    )


def test_crafts_and_games():
    assert tags("Japanese Kintsugi in Indiranagar") == {"ART-CRAFT/KINTSUGI"}
    assert "GAMES/SOCIAL-DEDUCTION" in tags("Mafia Night by The Fun Boardgames")
    assert "GAMES/BOARDGAMES" in tags("Social Boardgames Night")
    assert "GAMES/QUIZ" in tags("Pop Culture Quiz by Calm Your Wits Quizzing")


def test_near_misses():
    assert tags("Behrupiye - A Sketch Comedy Show") == {"SHOW/STANDUP"}
    assert not tags("Dance Improv: Move With Each Other")
    assert not tags("Garba Necklace Making")
    assert not tags("Battle Grid Paintball | Bengaluru")


def test_stage_and_books():
    assert tags("13 Day Hybrid Acting Intensive") == {"ON-STAGE/ACTING"}
    assert tags("Improv Comedy Night") == {"SHOW/IMPROV"}
    assert tags("Beginners Improv Workshop") == {"ON-STAGE/IMPROV"}
    assert "BOOKS/BOOK-CLUB" in tags("The Quiet Library: Read Together")


def test_games_are_not_theatre():
    botc = {"@type": "TheaterEvent", "name": "Blood on the Clocktower"}
    assert event_tags(botc, {"SHOW/THEATER": 0.9}) == {"GAMES", "GAMES/SOCIAL-DEDUCTION"}
    assert event_tags({"name": "Hamlet"}, {"SHOW/THEATER": 0.9}) == {"SHOW", "SHOW/THEATER"}
    night = {"name": "Board Game Night"}
    assert event_tags(night, {"SOCIAL/STRANGERS-MEETUP": 0.95}) == {"GAMES", "GAMES/BOARDGAMES"}
    # post-build.sql tags venues' game nights, and the tagger adds parents
    cafe = {"name": "Sunday Session", "keywords": ["GAMES/BOARDGAMES"]}
    assert event_tags(cafe, {}) == {"GAMES", "GAMES/BOARDGAMES"}


def test_club_nights_are_hidden():
    party = {"@type": "MusicEvent", "name": "Finch After Dark"}
    tags = event_tags(party, {"NIGHTLIFE/DJ": 0.9, "NIGHTLIFE/BOLLYWOOD": 0.9})
    assert tags == {"NIGHTLIFE", "NIGHTLIFE/DJ", "NIGHTLIFE/BOLLYWOOD", "LOW-QUALITY"}
    assert event_tags({"name": "Bollywood Karaoke Night"}, {}) == {
        "NIGHTLIFE",
        "NIGHTLIFE/KARAOKE",
        "LOW-QUALITY",
    }
    assert event_tags({"name": "AI meetup"}, {"TECH": 0.9}) == {"BUSINESS"}
    social = {"name": "Resin Geode Art Date", "location": {"name": "Koramangala Social"}}
    assert "LOW-QUALITY" in event_tags(social, {"ART-CRAFT": 0.9})
    assert "LOW-QUALITY" not in event_tags(social | {"name": "Gig"}, {})
    devotional = {"LIVE-MUSIC/DEVOTIONAL": 0.9}
    assert "LOW-QUALITY" in event_tags({"name": "Kirtan"}, devotional)
    skills = event_tags({"name": "Marketing 101"}, {"BUSINESS/SKILLS": 0.9})
    assert skills == {"BUSINESS", "BUSINESS/SKILLS"}
    pilates = event_tags({"name": "Reformer Pilates"}, {})
    assert pilates == {"FITNESS/PILATES", "FITNESS", "-CURATED"}


def test_audience():
    assert "WOMEN-ONLY" in tags(
        "Basketball with the Sisters", keywords=["SISTERSINSWEAT"]
    )
    assert "KIDS" in tags("Softplay for Kids", "ChildrensEvent")


def test_parents():
    assert with_parents({"SPORTS-SCREENING/CRICKET"}) == {
        "SPORTS-SCREENING/CRICKET",
        "SPORTS-SCREENING",
    }
    assert with_parents({"ART-CRAFT/KINTSUGI"}) == {"ART-CRAFT/KINTSUGI", "ART-CRAFT"}


def test_taxonomy():
    parents = {t.rpartition("/")[0] for t in TAGS if "/" in t}
    assert parents <= set(TAGS) | EXCLUDE
    assert all(tag in TAGS for tag, _ in RULES)
    assert all(tag in QUESTIONS for tag in THRESHOLDS)
    assert all(mode in (None, "experiential", "participatory") for mode, _ in TAGS.values())
    assert "QUEER" not in TAGS and "WOMEN-ONLY" not in QUESTIONS
    assert all(tag == tag.upper() for tag in TAGS)


class FakeJev:
    def __init__(self):
        self.asked = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def system_one(self, state, questions):
        name = state["event"]["name"]
        self.asked.append(name)
        assert set(questions) == set(QUESTIONS) | {"@type"}
        if name not in REPLIES:
            raise TypeSafeError("quota exceeded")
        nouls, kind, confidence = REPLIES[name]
        return SimpleNamespace(
            nouls={t: SimpleNamespace(noul=p) for t, p in nouls.items()},
            choices={"@type": SimpleNamespace(choice=kind, confidence=confidence)},
        )


@pytest.fixture
def jev(tmp_path, monkeypatch):
    client = FakeJev()
    monkeypatch.setattr(tagger, "clef", lambda: client)
    monkeypatch.setattr(tagger, "CACHE", tmp_path / "activities.sqlite")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    return client


def test_keywords_and_state():
    assert keywords({"keywords": "A,B"}) == []
    url, event = ROWS[1]
    event = state(event)["event"]
    assert event["name"].startswith("Horn OK Quiz")
    assert event["keywords"] == ["INDIRANAGAR"]
    assert event["venue"] and len(event["description"]) <= 600
    assert state({"organizer": "x", "location": None, "description": "a\n\n b"})[
        "event"
    ] == {
        "name": None,
        "type": None,
        "organizer": None,
        "venue": None,
        "keywords": [],
        "description": "a b",
    }


def test_ask_parses_answers(jev):
    answers = ask(jev, ROWS[0][1])
    assert answers == {
        "ART-CRAFT/KINTSUGI": 0.9,
        "ART-CRAFT": 0.8,
        "ART-CRAFT/POTTERY": 0.6,
        "@type": ["EducationEvent", 0.8],
    }
    assert ask(jev, ROWS[5][1]) is None


def test_thresholds():
    assert jev_tags(
        {"ART-CRAFT/POTTERY": 0.69, "ART-CRAFT/KINTSUGI": 0.5, "NOPE": 1, "@type": ["Event", 1]}
    ) == {"ART-CRAFT/KINTSUGI"}
    assert jev_type({"@type": ["EducationEvent", 0.5]}) == "EducationEvent"
    assert jev_type({"@type": ["EducationEvent", 0.4]}) is None
    assert jev_type({"@type": ["Event", 0.9]}) is None
    assert jev_type({}) is None


def test_answers_are_cached(jev):
    events = {u: e for u, e in (ROWS[0], ROWS[1], ROWS[3])}
    first = by_jev(events)
    assert len(jev.asked) == 3 and set(first) == set(events)
    assert by_jev(events) == first and len(jev.asked) == 3
    db = sqlite3.connect(tagger.CACHE)
    db.execute("UPDATE answers SET version = ?", (VERSION - 1,))
    db.commit()
    by_jev(events)
    assert len(jev.asked) == 6


def test_failed_calls_are_retried(jev):
    url, event = ROWS[5]
    assert by_jev({url: event}) == {}
    assert by_jev({url: event}) == {}
    assert jev.asked == [event["name"]] * 2


def test_no_key_uses_cache_only(jev, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY")
    assert by_jev({u: e for u, e in ROWS}) == {}
    assert jev.asked == []


def test_main_tags_and_types_events(jev, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conn = sqlite3.connect("events.db")
    conn.execute("CREATE TABLE events (url TEXT, event_json TEXT)")
    conn.executemany(
        "INSERT INTO events VALUES (?, ?)", [(u, json.dumps(e)) for u, e in ROWS]
    )
    conn.commit()
    tagger.main()
    out = [
        json.loads(e)
        for (e,) in conn.execute("SELECT event_json FROM events ORDER BY rowid")
    ]
    assert out[0]["@type"] == "EducationEvent"
    assert out[0]["keywords"][-2:] == ["ART-CRAFT", "ART-CRAFT/KINTSUGI"]
    # Both dates of one listing share a single Jev call
    assert (
        jev.asked.count(ROWS[1][1]["name"]) == 1 and ROWS[2][1]["name"] not in jev.asked
    )
    assert out[1]["@type"] == "Event"
    assert out[1]["keywords"][-4:] == ["EXPO", "GAMES", "GAMES/QUIZ", "LOW-QUALITY"]
    assert out[2]["@type"] == "SocialEvent" and "GAMES/QUIZ" in out[2]["keywords"]
    assert out[3]["@type"] == "EducationEvent"
    assert out[3]["keywords"][-2:] == ["ART-CRAFT", "ART-CRAFT/KINTSUGI"]
    assert out[4] == ROWS[4][1]
    assert out[5]["keywords"] == ["BLRBIRDERS", "BNGBIRDS", "OUTDOORS", "OUTDOORS/BIRDING"]
