from types import SimpleNamespace

from src.common import linktree

PAGE = "test/fixtures/linktree/page.html"


def fake_session(path, seen):
    def get(url):
        seen.append(url)
        return SimpleNamespace(content=open(path, "rb").read())
    return SimpleNamespace(get=get)


def test_classic_links_are_yielded(monkeypatch):
    seen = []
    monkeypatch.setattr(linktree, "get_cached_session", lambda: fake_session(PAGE, seen))
    links = list(linktree.Linktree("someclub").fetch_links())
    assert seen == ["https://linktr.ee/someclub"]
    assert links == [
        {"title": "Open Mic Night", "url": "https://example.com/open-mic", "thumbnail": "https://example.com/mic.jpg"},
        {"title": "Book Club", "url": "https://example.com/book-club", "thumbnail": None},
    ]
