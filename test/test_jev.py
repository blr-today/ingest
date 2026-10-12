from datetime import time
from types import SimpleNamespace

from common import jev
from common.tz import IST


def test_hours_are_labelled_for_the_model():
    assert jev.HOURS["0"] == "12 AM (00:00)"
    assert jev.HOURS["12"] == "12 PM (12:00)"
    assert jev.HOURS["19"] == "7 PM (19:00)"
    assert jev.MINUTES[0] == "0" and len(jev.MINUTES) == 60


def test_pick_adds_a_none_option():
    assert jev.pick("Which?", []) is None
    choice = jev.pick("Which?", ["a", "b"])
    assert choice.instructions == "Which?"
    assert choice.criteria == {"a": None, "b": None, "none": "None of these fits."}
    assert jev.pick("Which?", {"a": "first"}).criteria == {"a": "first", "none": "None of these fits."}


def test_time_questions_mention_the_subject():
    questions = jev.time_questions("the run")
    assert set(questions) == {"has_end", "start_hour", "start_minute", "end_hour", "end_minute"}
    assert "the run" in questions["has_end"].instructions
    assert set(questions["end_minute"].criteria) == set(jev.MINUTES) | {"none"}


def test_ask_skips_missing_questions_and_reads_answers():
    seen = {}

    def system_one(state, questions):
        seen.update(state=state, questions=questions)
        return SimpleNamespace(
            nouls={"has_end": SimpleNamespace(noul=0.9)},
            choices={"start_hour": SimpleNamespace(choice="18", confidence=0.8)},
        )
    client = SimpleNamespace(system_one=system_one)
    nouls, picks = jev.ask(client, {"text": "6 PM"}, {"has_end": "q1", "start_hour": "q2", "venue": None})
    assert seen == {"state": {"text": "6 PM"}, "questions": {"has_end": "q1", "start_hour": "q2"}}
    assert nouls == {"has_end": 0.9}
    assert picks == {"start_hour": ("18", 0.8)}


def test_value_needs_confidence():
    picks = {"a": ("7", 0.5), "b": ("7", 0.49), "c": ("none", 0.99)}
    assert jev.value(picks, "a") == "7"
    assert jev.value(picks, "b") is None
    assert jev.value(picks, "c") is None
    assert jev.value(picks, "missing") is None


def test_clock_builds_ist_times():
    picks = {"start_hour": ("18", 0.9), "start_minute": ("30", 0.9), "end_hour": ("20", 0.9)}
    assert jev.clock(picks, "start") == time(18, 30, tzinfo=IST)
    assert jev.clock(picks, "end") == time(20, 0, tzinfo=IST)
    assert jev.clock({}, "start") is None


def test_end_clock_needs_a_stated_later_end():
    picks = {"start_hour": ("18", 0.9), "end_hour": ("20", 0.9), "end_minute": ("15", 0.9)}
    assert jev.end_clock({"has_end": 0.7}, picks) == time(20, 15, tzinfo=IST)
    assert jev.end_clock({"has_end": 0.3}, picks) is None
    assert jev.end_clock({}, picks) is None
    early = picks | {"end_hour": ("17", 0.9)}
    assert jev.end_clock({"has_end": 0.9}, early) is None
    assert jev.end_clock({"has_end": 0.9}, {"end_hour": ("20", 0.9)}) is None
