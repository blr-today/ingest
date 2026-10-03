from processors.exhibition import Exhibition


def test_exhibitions_become_all_day():
    event = {
        "@type": "ExhibitionEvent",
        "startDate": "2026-11-24T10:00:00+05:30",
        "endDate": "2026-11-30T17:00:00+05:30",
    }
    result = Exhibition.process("u", event)
    assert (result["startDate"], result["endDate"]) == ("2026-11-24", "2026-11-30")


def test_other_events_keep_times():
    event = {"@type": "MusicEvent", "startDate": "2026-11-24T19:00:00+05:30"}
    assert Exhibition.process("u", event)["startDate"] == "2026-11-24T19:00:00+05:30"
