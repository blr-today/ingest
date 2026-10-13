import importlib
import pathlib
from types import SimpleNamespace

import pytest

from src.common import remote

FIXTURES = pathlib.Path("test/fixtures/remote").resolve()
GRAPH_URL = "https://bangaloreastronomyclub.com/event/orionids-meteor-shower-meteors-midnight-magic/"
EVENT_URL = "https://courtyardkoota.com/events/bengaluru-boy-by-danish-sait-stand-up-comedy/"
PAGES = {
    GRAPH_URL: (FIXTURES / "graph.html").read_text(),
    EVENT_URL: (FIXTURES / "event.html").read_text(),
    "https://example.com/about": "<html><head><title>About</title></head></html>",
}


@pytest.fixture
def site(tmp_path, monkeypatch):
    calls = []

    def get(url, headers=None, timeout=None):
        calls.append((url, headers))
        if url not in PAGES:
            raise ConnectionError("offline")
        return SimpleNamespace(text=PAGES[url], url=url)
    monkeypatch.setattr(remote, "get_cached_session", lambda: SimpleNamespace(get=get))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    return calls


def test_find_event_matches_known_types():
    items = [{"@type": "WebPage"}, {"@type": ["Organization", "Place"]}, {"@type": "MusicEvent", "n": 1}, {"@type": "Event"}]
    assert remote.find_event(items) == {"@type": "MusicEvent", "n": 1}
    assert remote.find_event([{"@type": "Place"}]) is None


def test_add_source_tags_list_keywords():
    assert remote.add_source({}, "koota") == {"keywords": ["KOOTA"]}
    event = remote.add_source({"keywords": ["COMEDY", "KOOTA"]}, "koota")
    assert sorted(event["keywords"]) == ["COMEDY", "KOOTA"]


def test_events_from_urls_keep_page_data(site, capsys):
    PAGES["https://example.com/short"] = (
        '<script type="application/ld+json">'
        '{"@type": "Event", "name": "Short", "url": "https://example.com/canonical"}</script>'
    )
    urls = [GRAPH_URL, "https://example.com/about", "", "https://example.com/down", "https://example.com/short\n", EVENT_URL]
    graph, short, koota = remote.events_from_urls(urls)
    assert graph["@id"] == GRAPH_URL + "#event"
    assert graph["startDate"] == "2026-10-20T16:00:00+05:30"
    assert short == {"@type": "Event", "name": "Short", "url": "https://example.com/canonical"}
    assert koota["name"] == "Bengaluru Boy by Danish Sait | Stand Up Comedy"
    assert "KOOTA" not in koota.get("keywords", []) and "BAC" not in graph.get("keywords", [])
    out = capsys.readouterr().out
    assert "Could not find event in https://example.com/about" in out
    assert "Error fetching https://example.com/down: offline" in out
    assert [url for url, _ in site] == [u.strip() for u in urls if u]
    assert all(h == remote.USER_AGENT_HEADERS for _, h in site)


def test_events_from_urls_skip_bad_pages(site, monkeypatch, capsys):
    PAGES["https://example.com/empty"] = ""
    PAGES["https://example.com/badjson"] = "<html></html>"
    PAGES["https://example.com/blank"] = " \n"
    real = remote.JsonLdExtractor

    class Extractor(real):
        def extract(self, text):
            if text == "<html></html>":
                raise remote.json.decoder.JSONDecodeError("bad", text, 0)
            return real().extract(text)
    monkeypatch.setattr(remote, "JsonLdExtractor", Extractor)
    urls = ["https://example.com/empty", "https://example.com/badjson", "https://example.com/blank", EVENT_URL]
    assert [e["name"] for e in remote.events_from_urls(urls)] == ["Bengaluru Boy by Danish Sait | Stand Up Comedy"]
    out = capsys.readouterr().out
    assert "No content for  https://example.com/empty" in out
    assert "Error parsing JSON for https://example.com/badjson" in out
    assert "Error parsing HTML for https://example.com/blank" in out


def test_page_url_fills_a_missing_event_url(site):
    PAGES["https://example.com/nourl"] = '<script type="application/ld+json">{"@type": "Event", "name": "No URL"}</script>'
    [event] = remote.events_from_urls(["https://example.com/nourl"])
    assert event == {"@type": "Event", "name": "No URL", "url": "https://example.com/nourl"}


def test_add_source_prefixes_string_keywords():
    assert remote.add_source({"keywords": "comedy"}, "koota") == {"keywords": "KOOTA, comedy"}


@pytest.mark.parametrize("name", ["allevents", "koota"])
def test_url_list_sources_read_out_txt(site, name):
    pathlib.Path(f"out/{name}.txt").write_text(f"{EVENT_URL}\n\nhttps://example.com/about\n")
    [event] = importlib.import_module(f"src.sources.{name}").events()
    assert event["name"] == "Bengaluru Boy by Danish Sait | Stand Up Comedy"
    assert [url for url, _ in site] == [EVENT_URL, "https://example.com/about"]
