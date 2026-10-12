import importlib.util
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

PATH = Path(__file__).parent.parent / "src/sources/together-buzz.py"
spec = importlib.util.spec_from_file_location("together_buzz", PATH)
together = importlib.util.module_from_spec(spec)
spec.loader.exec_module(together)


def item(days, action):
    start = (date.today() + timedelta(days=days)).isoformat() + "T18:30:00.000Z"
    return {"data": {"start_datetime": start, "action": action}}


# api.together.buzz no longer resolves, so the payload is shaped after the parser
def test_urls_today_and_later(monkeypatch):
    data = {"data": [item(-1, "https://together.buzz/e/past"), item(0, "https://together.buzz/e/today"), item(3, "https://together.buzz/e/soon")]}
    urls = []

    def get(url):
        urls.append(url)
        return SimpleNamespace(json=lambda: data)

    monkeypatch.setattr(together, "get_cached_session", lambda: SimpleNamespace(get=get))
    assert together.urls() == ["https://together.buzz/e/today", "https://together.buzz/e/soon"]
    assert urls == ["https://api.together.buzz/v1/discovery/home?format=json&limit=10&pageCount=1"]
