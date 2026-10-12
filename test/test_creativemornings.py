import datetime
import json
import runpy
import subprocess
from pathlib import Path
from types import SimpleNamespace

import creativemornings

CITY = (Path(__file__).parent / "fixtures/creativemornings/city-blr.html").read_text()


# Past talk pages carry no JSON-LD, so talk pages here are minimal stand-ins
def talk(name, start):
    data = {"@context": "https://schema.org", "@type": "Event", "name": name, "startDate": start}
    return f'<script type="application/ld+json">{json.dumps(data)}</script>'


class Fixed(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime.datetime(2026, 10, 12, tzinfo=tz)


def serve(monkeypatch, pages):
    rendered = []

    def render(url, wait_for):
        rendered.append(url)
        return pages[url]

    monkeypatch.setattr(creativemornings, "render", render)
    monkeypatch.setattr(creativemornings, "datetime", Fixed)
    return rendered


def test_render_uses_lightpanda(monkeypatch):
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(stdout="<html></html>")

    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setenv("LIGHTPANDA", "/opt/lightpanda")
    assert creativemornings.render("https://creativemornings.com/cities/BLR", "a") == "<html></html>"
    [(args, kwargs)] = calls
    assert args[0] == "/opt/lightpanda" and args[-1] == "https://creativemornings.com/cities/BLR"
    assert "document.querySelector('a')" in args
    assert kwargs["env"]["LIGHTPANDA_DISABLE_TELEMETRY"] == "true"


def test_city_page_without_upcoming_talks(monkeypatch):
    rendered = serve(monkeypatch, {"https://creativemornings.com/cities/BLR": CITY})
    assert creativemornings.scrape_cm("BLR") == []
    assert rendered == ["https://creativemornings.com/cities/BLR"]


def test_upcoming_talks(monkeypatch, capsys):
    base = "https://creativemornings.com/talks/"
    links = '<a href="/talks/play">x</a><a href="/talks/old">x</a><a href="/talks/empty">x</a>'
    serve(monkeypatch, {
        "https://creativemornings.com/cities/BLR": CITY.replace("</body>", links + "</body>"),
        base + "play": talk("Play", "2026-10-24T03:30:00Z"),
        base + "old": talk("Old", "2026-09-26T03:30:00Z"),
        base + "empty": "<html></html>",
    })
    [event] = creativemornings.scrape_cm("BLR")
    assert event["name"] == "Play"
    assert event["url"] == base + "play"
    out = capsys.readouterr().out
    assert "No event in " + base + "empty" in out
    assert "Event in past: " + base + "old" in out


def test_main_writes_events(monkeypatch, tmp_path):
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: SimpleNamespace(stdout=CITY))
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    runpy.run_module("creativemornings", run_name="__main__")
    assert json.loads((tmp_path / "out/creativemornings.json").read_text()) == []
