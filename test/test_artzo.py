import json
import runpy
from pathlib import Path
from types import SimpleNamespace

import pytest

import src.common.session
from src.sources.artzo import URL, fetch_events

HTML = (Path(__file__).parent / "fixtures/artzo/events-and-workshops.html").read_text()
WIDGET = '"widgetcomp-mkdxhyzj2": {"events": {"events": []'


def session(html=HTML):
    def get(url):
        assert url == URL
        return SimpleNamespace(text=html)

    return SimpleNamespace(get=get)


def test_no_listed_events(capsys):
    fetch_events(session())
    assert capsys.readouterr().out == ""


def test_prints_event_urls(capsys):
    events = json.dumps([{"slug": "watercolour-basics"}, {"slug": "clay-day"}])
    fetch_events(session(HTML.replace(WIDGET, WIDGET[:-2] + events)))
    assert capsys.readouterr().out.splitlines() == [
        "https://www.artzo.in/event-details/watercolour-basics",
        "https://www.artzo.in/event-details/clay-day",
    ]


def test_page_without_events_widget(capsys):
    fetch_events(session(HTML.replace('"events": {"events"', '"other": {"events"')))
    fetch_events(session(HTML.replace('"appsWarmupData"', '"apps"')))
    assert capsys.readouterr().out == ""


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_main(monkeypatch, capsys):
    monkeypatch.setattr(src.common.session, "get_cached_session", session)
    runpy.run_module("src.sources.artzo", run_name="__main__")
    assert capsys.readouterr().out == ""
