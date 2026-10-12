import json
from pathlib import Path
from types import SimpleNamespace

import mapindia

FIXTURES = Path(__file__).parent / "fixtures/mapindia"
EVENT = "https://map-india.org/map-events/drawing-the-everyday/"
# Post ids are real; where the other two redirect to is made up for the test
LOCATIONS = {
    "https://map-india.org/?p=23191": EVENT,
    "https://map-india.org/?p=23207": "https://map-india.org/map-exhibitions/an-exhibit/",
    "https://map-india.org/?p=23194": "https://map-india.org/map-events/no-calendar/",
}


class FakeSession:
    def __init__(self):
        self.posted = []

    def post(self, url, headers, data):
        self.posted.append(data)
        page = "ajax-2.json" if "excludeIds[]" in data else "ajax-1.json"
        return SimpleNamespace(json=lambda: json.loads((FIXTURES / page).read_text()))

    def head(self, url, headers):
        return SimpleNamespace(headers={"Location": LOCATIONS[url]})

    def get(self, url, headers):
        files = {EVENT: "drawing-the-everyday.html", EVENT + "ical/": "drawing-the-everyday.ics"}
        if url not in files:
            return SimpleNamespace(status_code=404, text="")
        return SimpleNamespace(status_code=200, text=(FIXTURES / files[url]).read_text())


def test_fetch_urls_loads_more(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(mapindia, "session", session)
    assert list(mapindia.fetch_urls()) == list(LOCATIONS)
    assert session.posted == [
        {"action": "load_filtered_events"},
        {"action": "load_filtered_events", "excludeIds[]": ["23191", "23207"]},
    ]


def test_calendar_keeps_events_with_ical(monkeypatch):
    monkeypatch.setattr(mapindia, "session", FakeSession())
    [event] = mapindia.generate_calendar().events
    assert event.name == "Drawing the Everyday"
    assert event.categories == ["Workshops", "MAP", "CBD"]
    assert event.begin.isoformat() == "2026-10-17T05:30:00+00:00"


def test_main_writes_ics(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(mapindia, "session", FakeSession())
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    mapindia.main()
    assert "SUMMARY:Drawing the Everyday" in (tmp_path / "out/mapindia.ics").read_text()
    assert "[MAP] 1 events" in capsys.readouterr().out
