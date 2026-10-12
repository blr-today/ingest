import pathlib
from types import SimpleNamespace

import pytest

from common import remote

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

    def get(url, headers=None):
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


def test_fetches_events_from_url_lists(site, capsys):
    pathlib.Path("out/bac.txt").write_text(f"{GRAPH_URL}\nhttps://example.com/about\nhttps://example.com/down\n")
    pathlib.Path("out/koota.txt").write_text(EVENT_URL + "\n")
    got = dict(remote.fetch_remote_events())
    assert set(got) == {GRAPH_URL, EVENT_URL}
    graph = got[GRAPH_URL]
    assert graph["@id"] == GRAPH_URL + "#event"
    assert graph["startDate"] == "2026-10-20T16:00:00+05:30"
    assert graph["keywords"] == ["BAC"]
    assert got[EVENT_URL]["name"] == "Bengaluru Boy by Danish Sait | Stand Up Comedy"
    assert got[EVENT_URL]["keywords"] == ["KOOTA"]
    out = capsys.readouterr().out
    assert "Could not find event in https://example.com/about" in out
    assert "Error fetching https://example.com/down: offline" in out
    assert all(h == remote.USER_AGENT_HEADERS for _, h in site)


def test_file_filter_limits_sources(site):
    pathlib.Path("out/bac.txt").write_text(GRAPH_URL + "\n")
    pathlib.Path("out/koota.txt").write_text(EVENT_URL + "\n")
    got = list(remote.fetch_remote_events("out/koota.txt"))
    assert [url for url, _ in got] == [EVENT_URL]
    assert [url for url, _ in site] == [EVENT_URL]
