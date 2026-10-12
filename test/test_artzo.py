import json
from pathlib import Path
from types import SimpleNamespace

from src.sources import artzo
from src.sources.artzo import URL, fetch_events

HTML = (Path(__file__).parent / "fixtures/artzo/events-and-workshops.html").read_text()
WIDGET = '"widgetcomp-mkdxhyzj2": {"events": {"events": []'


def session(html=HTML):
    def get(url):
        assert url == URL
        return SimpleNamespace(text=html)

    return SimpleNamespace(get=get)


def test_no_listed_events():
    assert fetch_events(session()) == []


def test_lists_event_urls():
    events = json.dumps([{"slug": "watercolour-basics"}, {"slug": "clay-day"}])
    assert fetch_events(session(HTML.replace(WIDGET, WIDGET[:-2] + events))) == [
        "https://www.artzo.in/event-details/watercolour-basics",
        "https://www.artzo.in/event-details/clay-day",
    ]


def test_page_without_events_widget():
    assert fetch_events(session(HTML.replace('"events": {"events"', '"other": {"events"'))) == []
    assert fetch_events(session(HTML.replace('"appsWarmupData"', '"apps"'))) == []


def test_urls_and_events(monkeypatch):
    monkeypatch.setattr(artzo, "get_cached_session", session)
    monkeypatch.setattr(artzo, "events_from_urls", lambda urls: [{"url": u} for u in urls])
    assert artzo.urls() == []
    assert artzo.events() == []
