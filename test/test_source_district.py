import json
from pathlib import Path

import pytest

from src.sources import district

FIXTURES = Path(__file__).parent / "fixtures" / "source_district"
WORKSHOP = "https://district.in/modular-type-workshop-by-a-letter-atelier-sep19-2026/event"
IMPROV = "https://district.in/whimsical-wednesday-with-improv-lore/event"


class FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.content = text.encode()
        self.status_code = status_code
        self.headers = {"content-type": "application/json", "server": "fake"}

    def json(self):
        return json.loads(self.text)


class FakeSession:
    def __init__(self, responses=(), pages=None):
        self.responses = list(responses)
        self.pages = pages or {}
        self.bodies = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.bodies.append(json)
        return self.responses.pop(0)

    def get(self, url, headers=None, timeout=None):
        if url not in self.pages:
            raise ConnectionError(url)
        return FakeResponse(self.pages[url])


def discovery(page):
    return FakeResponse((FIXTURES / f"discovery-{page}.json").read_text())


def test_event_data_walks_nested_rails():
    rails = json.loads((FIXTURES / "discovery-1.json").read_text())["EDSResponse"]["rails"]
    events = list(district.event_data(rails))
    assert [e.get("event_slug") for e in events] == [
        "experience-dosa-and-chutney-making-sep7-2026",
        "somad-halloween-carnival-2026-oct31-2026",
        None,
        "midautumn-festival-sep26-2026",
        "private-karaoke-booths-sep6-2026",
        "four-regions-reimagined-thai-culinary-journey-oct10-2026",
    ]
    assert events[0]["city"] == "Bengaluru"


def test_pages_load_more_until_done(capsys):
    session = FakeSession([discovery(1), discovery(2)])
    pages = list(district.pages(session))
    assert len(pages) == 2
    first, second = session.bodies
    assert first == {"location": district.LOCATION, "layout_type": "events_home_v2"}
    assert second["request_type"] == "load_more"
    assert second["postback_params"] == pages[0]["postback_params"]
    assert "[DISTRICT] page 1 has_more False" in capsys.readouterr().err


def test_pages_stop_at_limit():
    session = FakeSession([discovery(1), discovery(1)])
    assert len(list(district.pages(session, limit=2))) == 2


def test_post_falls_back_to_curl(monkeypatch, capsys):
    blocked = FakeResponse("<html>Access Denied</html>", 403)
    monkeypatch.setattr(district.curl_cffi, "post", lambda *a, **kw: discovery(2))
    assert district.post(FakeSession([blocked]), {})["EDSResponse"]["has_more"] is False
    assert "non-JSON body: <html>Access Denied</html>" in capsys.readouterr().err


def test_post_raises_when_both_clients_are_blocked(monkeypatch):
    blocked = FakeResponse("<html>Access Denied</html>", 403)
    monkeypatch.setattr(district.curl_cffi, "post", lambda *a, **kw: blocked)
    with pytest.raises(ValueError):
        district.post(FakeSession([blocked]), {})


def test_page_event_reads_json_ld():
    session = FakeSession(pages={WORKSHOP: (FIXTURES / "modular-type-workshop.html").read_text()})
    event = district.page_event(session, WORKSHOP)
    assert event["@type"] == "Event"
    assert event["name"] == "Modular Type Workshop by A Letter Atelier"


def test_page_event_reads_graph():
    html = (FIXTURES / "modular-type-workshop.html").read_text()
    start = html.index('{"@context"')
    end = html.index("</script>", start)
    graph = json.dumps({"@context": "https://schema.org", "@graph": [json.loads(html[start:end])]})
    session = FakeSession(pages={WORKSHOP: html[:start] + graph + html[end:]})
    assert district.page_event(session, WORKSHOP)["name"] == "Modular Type Workshop by A Letter Atelier"


def test_page_without_event_or_unreachable(capsys):
    session = FakeSession(pages={IMPROV: (FIXTURES / "whimsical-wednesday.html").read_text()})
    assert district.page_event(session, IMPROV) is None
    assert district.page_event(session, WORKSHOP) is None
    assert f"Error fetching {WORKSHOP}: {WORKSHOP}" in capsys.readouterr().out


@pytest.fixture
def cache(monkeypatch, tmp_path):
    monkeypatch.setenv("DISTRICT_CACHE", str(tmp_path))
    monkeypatch.setattr(district, "today", lambda: "2026-10-16")
    return tmp_path


def page(slug, start, fetched):
    return {"fetched": fetched, "event": {"name": slug, "startDate": start}}


def test_crawl_fetches_new_then_stale_pages_within_budget(monkeypatch, cache):
    now = district.time.time()
    old = {
        "kept": page("kept", "2026-10-30", now),
        "stale": page("stale", "2026-10-16", now - district.DAY),
        "gone": page("gone", "2026-10-20", now),
    }
    district.save(old)
    monkeypatch.setattr(district, "slugs", lambda: {"kept", "stale", "new"})
    fetched = []

    def fake_page(session, url):
        fetched.append(url.split("/")[3])
        return {"name": "fresh", "startDate": "2026-10-17"}

    monkeypatch.setattr(district, "page_event", fake_page)
    monkeypatch.setenv("DISTRICT_MAX_FETCHES", "1")
    found = district.crawl()
    assert fetched == ["new"]
    assert sorted(found) == ["kept", "new", "stale"]
    monkeypatch.setenv("DISTRICT_MAX_FETCHES", "5")
    fetched.clear()
    district.crawl()
    assert fetched == ["stale"]
    assert district.load()["pages"]["stale"]["event"]["name"] == "fresh"


def test_crawl_keeps_a_fuller_saved_copy(monkeypatch, cache):
    district.save({s: page(s, "2026-10-20", district.time.time()) for s in "abcd"})
    monkeypatch.setattr(district, "slugs", lambda: {"a"})
    with pytest.raises(RuntimeError):
        district.crawl()
    assert len(district.load()["pages"]) == 4


def test_builds_read_upcoming_saved_events(monkeypatch, cache):
    monkeypatch.delenv("DISTRICT_CRAWL", raising=False)
    now = district.time.time()
    district.save({
        "past": page("past", "2026-10-15T19:00", now),
        "running": {"fetched": now, "event": {"name": "running", "startDate": "2026-10-01", "endDate": "2026-10-20"}},
        "soon": page("soon", "2026-10-16T19:00", now),
    })
    assert sorted(e["name"] for e in district.events()) == ["running", "soon"]


def test_saved_pages_expire_after_a_week(cache, capsys):
    district.save({"a": page("a", "2026-10-20", 0)})
    data = json.loads(Path(district.cache_path()).read_text())
    Path(district.cache_path()).write_text(json.dumps(data | {"listed": data["listed"] - 3 * district.DAY}))
    assert list(district.saved()) == ["a"]
    assert "using pages from 72h ago" in capsys.readouterr().err
    Path(district.cache_path()).write_text(json.dumps(data | {"listed": 0}))
    with pytest.raises(RuntimeError):
        district.saved()
