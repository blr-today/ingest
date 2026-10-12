import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.sources import eventbrite as source
from src.sources import pumarun

ROOT = Path(__file__).parent.parent
HTML = (Path(__file__).parent / "fixtures/source_eventbrite/organizer.html").read_bytes()
RUN = "https://www.eventbrite.com/e/bangalore-marathon-shakeout-run-tickets-2002205535655"


@pytest.fixture
def requested(monkeypatch, tmp_path):
    urls = []

    def get(url):
        urls.append(url)
        return SimpleNamespace(content=HTML)

    monkeypatch.setattr(source.eventbrite, "get_cached_session", lambda: SimpleNamespace(get=get))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "in").mkdir()
    shutil.copy(ROOT / "in/known-hosts.yml", tmp_path / "in/known-hosts.yml")
    return urls


def test_urls_read_known_hosts(requested):
    assert source.urls("pumarun") == [RUN]
    assert requested == ["https://www.eventbrite.com/o/87498853333"]


def test_pumarun_events(requested, monkeypatch):
    monkeypatch.setattr(source, "events_from_urls", lambda urls: [{"url": u} for u in urls])
    assert pumarun.events() == [{"url": RUN}]
    assert requested == ["https://www.eventbrite.com/o/87498853333"]
    assert not (Path("out") / "pumarun.txt").exists()
