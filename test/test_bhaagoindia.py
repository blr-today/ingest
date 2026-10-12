from src.processors.bhaagoindia import BhaagoIndia


def test_human_dates_become_ist():
    event = {
        "startDate": "Sept. 14, 2026, 5:30 a.m.",
        "endDate": "Sun, Sep 14, 2026 9 a.m.",
    }
    assert BhaagoIndia.process("u", event) == {
        "startDate": "2026-09-14T05:30:00+05:30",
        "endDate": "2026-09-14T09:00:00+05:30",
    }


def test_afternoon_dates():
    event = {
        "startDate": "March 1, 2026, 6 p.m.",
        "endDate": "March 1, 2026, 9:15 p.m.",
    }
    event = BhaagoIndia.process("u", event)
    assert event["startDate"] == "2026-03-01T18:00:00+05:30"
    assert event["endDate"] == "2026-03-01T21:15:00+05:30"
