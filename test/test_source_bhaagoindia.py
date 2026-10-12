from pathlib import Path
from types import SimpleNamespace

from src.sources import bhaagoindia
from src.sources.bhaagoindia import extract_event_urls, is_valid_event_url

HTML = (Path(__file__).parent / "fixtures/source_bhaagoindia/events.html").read_text()


def serve(monkeypatch, html):
    seen = []

    def get(url):
        seen.append(url)
        return SimpleNamespace(content=html.encode())

    monkeypatch.setattr(bhaagoindia.requests, "get", get)
    return seen


def test_valid_event_urls():
    assert is_valid_event_url("/events/tcs-world-10k-bengaluru/")
    assert is_valid_event_url("/events/tcs-world-10k-bengaluru")
    assert not is_valid_event_url("/events/")
    assert not is_valid_event_url("/events/city/bengaluru-4/")
    assert not is_valid_event_url("/blogs/some-post/")
    assert not is_valid_event_url(None)


def test_listing_page_has_no_event_links(monkeypatch, capsys):
    seen = serve(monkeypatch, HTML)
    extract_event_urls()
    assert seen == ["https://bhaagoindia.com/events/?city=bengaluru-4"]
    assert capsys.readouterr().out == ""


def test_event_links_are_sorted_and_unique(monkeypatch, capsys):
    extra = '<a href="/events/b-run/">B</a><a href="/events/a-run/">A</a><a href="/events/b-run/">B</a>'
    serve(monkeypatch, HTML.replace("</body>", extra + "</body>"))
    extract_event_urls("https://bhaagoindia.com/events/")
    assert capsys.readouterr().out.splitlines() == [
        "https://bhaagoindia.com/events/a-run/",
        "https://bhaagoindia.com/events/b-run/",
    ]
