from datetime import timedelta
from types import SimpleNamespace

import src.common.fetch as fetch_module
import src.common.session as session_module


def test_cached_session_uses_common_cache_configuration(monkeypatch):
    calls = []

    assert fetch_module.get_cached_session is session_module.get_cached_session

    class FakeCachedSession:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(session_module, "CachedSession", FakeCachedSession)

    session_module.get_cached_session()
    session_module.get_cached_session(
        "shared-cache",
        3,
        (200, 201),
        ["GET", "POST"],
        "memory",
        "json",
    )

    assert calls == [
        {
            "cache_name": "event-fetcher-cache",
            "expire_after": timedelta(days=1),
            "stale_if_error": True,
            "use_cache_dir": True,
            "cache_control": False,
            "allowable_codes": (200,),
            "allowable_methods": ["GET"],
            "backend": "sqlite",
            "serializer": None,
        },
        {
            "cache_name": "shared-cache",
            "expire_after": timedelta(days=3),
            "stale_if_error": True,
            "use_cache_dir": True,
            "cache_control": False,
            "allowable_codes": (200, 201),
            "allowable_methods": ["GET", "POST"],
            "backend": "memory",
            "serializer": "json",
        }
    ]


def test_fetch_uses_shared_session_factory_and_keeps_browser(monkeypatch):
    created_sessions = []

    class FakeCachedSession:
        def __init__(self, **kwargs):
            self.cache = SimpleNamespace()
            self.options = kwargs
            created_sessions.append(self)

    monkeypatch.setattr(session_module, "CachedSession", FakeCachedSession)

    fetch = fetch_module.Fetch(
        cache={
            "name": "fetch-cache",
            "days": 2,
            "allowable_codes": (200, 302),
            "allowable_methods": ["GET", "HEAD", "POST"],
            "backend": "memory",
            "serializer": "json",
        },
        browser="chrome",
    )

    assert fetch.session is created_sessions[0]
    assert fetch.cache is fetch.session.cache
    assert fetch.browser == "chrome"
    assert fetch.session.options == {
        "cache_name": "fetch-cache",
        "expire_after": timedelta(days=2),
        "stale_if_error": True,
        "use_cache_dir": True,
        "cache_control": False,
        "allowable_codes": (200, 302),
        "allowable_methods": ["GET", "HEAD", "POST"],
        "backend": "memory",
        "serializer": "json",
    }

    calls = []
    monkeypatch.setattr(fetch_module.curl, "request", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(fetch_module, "CorrectResponse", lambda request, response: response)

    result = fetch.request("GET", url="https://example.test/events", cache=False)

    assert result is None
    assert calls == [
        {
            "method": "GET",
            "impersonate": "chrome",
            "url": "https://example.test/events",
        }
    ]
