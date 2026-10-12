import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.sources import eventbrite as source

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
    (tmp_path / "out").mkdir()
    return urls


def test_write_urls(requested, tmp_path, capsys):
    source.write_urls("pumarun", "87498853333")
    assert (tmp_path / "out/pumarun.txt").read_text() == RUN + "\n"
    assert requested == ["https://www.eventbrite.com/o/87498853333"]
    assert "[EVENTBRITE/pumarun] 1 events" in capsys.readouterr().err


def test_main_reads_known_hosts(requested, monkeypatch, tmp_path):
    (tmp_path / "in").mkdir()
    shutil.copy(ROOT / "in/known-hosts.yml", tmp_path / "in/known-hosts.yml")
    monkeypatch.setattr(sys, "argv", ["eventbrite", "pumarun"])
    source.main()
    assert requested == ["https://www.eventbrite.com/o/87498853333"]
    assert (tmp_path / "out/pumarun.txt").read_text() == RUN + "\n"
