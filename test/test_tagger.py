from common.activities import TAGS, THRESHOLDS, with_parents
from tagger import RULES, by_rules


def tags(name, type_="Event", keywords=()):
    return by_rules({"@type": type_, "name": name, "keywords": list(keywords)})


def test_sports_screenings():
    assert "F1-SCREENING" in tags("F1 Singapore Grand Prix | Live Screening | Watson's")
    assert "CRICKET-SCREENING" in tags("Screening of India vs West Indies | The Studs")
    assert not tags("BENGALURU RUN by KAR IES") & {"F1-SCREENING", "SPORTS-SCREENING"}


def test_movie_screening_skips_sports():
    assert "MOVIE-SCREENING" in tags("Screening of Eat Pray Love", "ScreeningEvent")
    assert "MOVIE-SCREENING" not in tags(
        "F1 Italy Grand Prix | Live Screening", "ScreeningEvent"
    )


def test_crafts_and_games():
    assert tags("Japanese Kintsugi in Indiranagar") == {"KINTSUGI"}
    assert "SOCIAL-DEDUCTION" in tags("Mafia Night by The Fun Boardgames")
    assert "BOARDGAMES" in tags("Social Boardgames Night")
    assert "QUIZZING" in tags("Pop Culture Quiz by Calm Your Wits Quizzing")


def test_near_misses():
    assert tags("Behrupiye - A Sketch Comedy Show") == {"STANDUP-COMEDY"}
    assert not tags("Dance Improv: Move With Each Other")
    assert not tags("Garba Necklace Making")
    assert not tags("Battle Grid Paintball | Bengaluru")


def test_stage_and_books():
    assert "THEATER" in tags("13 Day Hybrid Acting Intensive")
    assert "BOOK-CLUB" in tags("The Quiet Library: Read Together")


def test_audience():
    assert "WOMEN-ONLY" in tags(
        "Basketball with the Sisters", keywords=["SISTERSINSWEAT"]
    )
    assert "KIDS" in tags("Softplay for Kids", "ChildrensEvent")


def test_parents():
    assert with_parents({"IPL-SCREENING"}) == {
        "IPL-SCREENING",
        "CRICKET-SCREENING",
        "SPORTS-SCREENING",
    }
    assert with_parents({"KINTSUGI"}) == {"KINTSUGI", "ART-CRAFT"}


def test_taxonomy():
    assert all(parent in TAGS for parent, _ in TAGS.values() if parent)
    assert all(tag in TAGS for tag, _ in RULES)
    assert all(tag in TAGS for tag in THRESHOLDS)
    assert all(tag == tag.upper() for tag in TAGS)
