import time
from src.processors.schemafixer import EDGES, SchemaFixer, get_domain


def clean(name):
    return EDGES.sub("", name) or name


def test_strips_edge_emoji():
    assert (
        clean("💬 THURSTALK #01: WHY MUSIC MOVES US")
        == "THURSTALK #01: WHY MUSIC MOVES US"
    )
    assert (
        clean("🌠 Astro-Photography Exhibition-4.0 🌠")
        == "Astro-Photography Exhibition-4.0"
    )
    assert clean("￼SHORT CIRCUIT 3.0") == "SHORT CIRCUIT 3.0"


def test_keeps_inner_symbols_and_emoji_only_names():
    assert clean("Rock ★ Night 🎸 Live") == "Rock ★ Night 🎸 Live"
    assert clean("🎉🎉") == "🎉🎉"


def fix(event, url="https://courtyardkoota.com/events/x/"):
    return SchemaFixer.process(url, event)


def test_names_are_unescaped():
    assert (
        fix({"name": "Tom &amp; Jerry 🎉", "startDate": "2026-10-25T12:00+05:30"})[
            "name"
        ]
        == "Tom & Jerry"
    )
    assert (
        fix({"name": "🎉🎉", "startDate": "2026-10-25T12:00+05:30"})["name"] == "🎉🎉"
    )


def test_dates_move_to_ist():
    event = fix(
        {"startDate": "2026-10-11T08:30:00.000Z", "endDate": "2026-10-11T11:30:00.000Z"}
    )
    assert event["startDate"] == "2026-10-11T14:00:00+05:30"
    assert event["endDate"] == "2026-10-11T17:00:00+05:30"


def test_missing_end_is_two_hours_later():
    event = fix({"startDate": "2026-10-25T12:00+05:30"})
    assert event["endDate"] == "2026-10-25T14:00:00+05:30"
    assert event["url"] == "https://courtyardkoota.com/events/x/"
    assert event["@context"] == "https://schema.org"


def test_bad_dates_are_kept(capsys):
    event = fix({"url": "https://a/b", "startDate": "Oct 5", "endDate": "soon"})
    assert (event["startDate"], event["endDate"]) == ("Oct 5", "soon")
    assert "Error parsing startDate for https://a/b" in capsys.readouterr().out


def test_single_organizer_and_location():
    event = fix(
        {
            "startDate": "2026-10-25T12:00+05:30",
            "organizer": [{"name": "A"}],
            "LOCATION": "Koota",
        }
    )
    assert event["organizer"] == {"name": "A"}
    assert event["location"] == "Koota" and "LOCATION" not in event
    two = [{"name": "A"}, {"name": "B"}]
    assert (
        fix({"startDate": "2026-10-25T12:00+05:30", "organizer": two})["organizer"]
        == two
    )


def test_keywords_become_a_clean_list():
    def keywords(value):
        return fix({"startDate": "2026-10-25T12:00+05:30", "keywords": value})[
            "keywords"
        ]

    assert keywords(" Modular Type Workshop , All,All") == [
        "Modular Type Workshop",
        "All",
    ]
    assert keywords({"@type": "Description", "content": "Comedy ,All"}) == [
        "Comedy",
        "All",
    ]
    assert keywords(["KOOTA", " KOOTA ", "", 5]) == ["KOOTA"]
    assert keywords(None) == []


def test_get_domain():
    assert get_domain("https://www.district.in/events/x") == "district.in"
    assert get_domain("https://allevents.in/bangalore/1") == "allevents.in"


def test_naive_dates_are_local(monkeypatch):
    monkeypatch.setenv("TZ", "UTC")
    time.tzset()
    try:
        event = fix({"startDate": "2026-10-17T20:00:00"})
    finally:
        monkeypatch.undo()
        time.tzset()
    assert event["startDate"] == "2026-10-17T20:00:00+05:30"
    assert event["endDate"] == "2026-10-17T22:00:00+05:30"


def test_missing_or_bad_start_is_left_alone(capsys):
    assert "endDate" not in fix({"name": "No date"})
    assert "endDate" not in fix({"startDate": "Oct 5"})


def test_odd_names_and_starts_are_kept(caplog, capsys):
    event = fix({"name": ["A", "B"], "startDate": None})
    assert event["name"] == ["A", "B"]
    assert event["startDate"] is None and "endDate" not in event
    assert "SchemaFixer found a name that is not text for https://courtyardkoota" in caplog.text
    assert "[IMP] Error parsing startDate" in capsys.readouterr().out
