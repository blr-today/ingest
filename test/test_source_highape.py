import json
from pathlib import Path
from types import SimpleNamespace

from src.sources import highape

DATA = json.loads((Path(__file__).parent / "fixtures/source_highape/section.json").read_text())
URLS = [
    "https://www.highape.com/bangalore/events/navratri-utsav-2026-by-jsma-upi6w1axb4",
    "https://www.highape.com/bangalore/events/wfv-siga-navratri-utsav-2026-xx6tb4i5r4",
    "https://www.highape.com/bangalore/events/navrang-navratri-season-3-at-dnd-hsr-onqpy7hr9r",
]


def serve(monkeypatch):
    calls = []

    def get(url, params, headers):
        calls.append((url, params, headers))
        return SimpleNamespace(json=lambda: DATA)

    monkeypatch.setattr(highape.requests, "get", get)
    return calls


def test_event_urls(monkeypatch):
    calls = serve(monkeypatch)
    assert list(highape.scrape_highape("bangalore")) == URLS
    [(url, params, headers)] = calls
    assert url == "https://www.highape.com/desktop/api/bangalore/pages/1/sections/3"
    assert params == {"search": "", "page": 1}
    assert headers == {"Accept-Encoding": "gzip"}


def test_urls(monkeypatch):
    serve(monkeypatch)
    assert highape.urls() == URLS


def test_events_fetch_sorted_urls(monkeypatch):
    serve(monkeypatch)
    monkeypatch.setattr(highape, "events_from_urls", lambda urls: [{"url": u} for u in urls])
    assert highape.events() == [{"url": u} for u in sorted(URLS)]
