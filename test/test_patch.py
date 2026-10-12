import json

import pytest

from src.processors.patch import Patch, get_patch, get_root_domain_easy


@pytest.fixture
def patches(tmp_path, monkeypatch):
    (tmp_path / "patch").mkdir()
    patch = {
        "@context": "https://schema.org",
        "keywords": ["HIGHAPE"],
        "inLanguage": "en",
    }
    (tmp_path / "patch/highape.com.json").write_text(json.dumps(patch))
    (tmp_path / "patch/tonight.is.json").write_text(
        '{"organizer": {"name": "Tonight"}}'
    )
    monkeypatch.chdir(tmp_path)
    get_patch.cache_clear()
    yield
    get_patch.cache_clear()


def test_root_domain():
    assert (
        get_root_domain_easy("https://www.highape.com/bangalore/events/x")
        == "highape.com"
    )
    assert get_root_domain_easy("https://cdn.district.in/a") == "cdn.district.in"


def test_unknown_sites_are_untouched(patches):
    event = {"name": "x"}
    assert Patch.process("https://example.com/e", event) is event
    assert get_patch("https://example.com/e") is None


def test_event_values_win(patches):
    event = Patch.process(
        "https://www.highape.com/e", {"name": "x", "inLanguage": "hi"}
    )
    assert event == {
        "@context": "https://schema.org",
        "keywords": ["HIGHAPE"],
        "inLanguage": "hi",
        "name": "x",
    }


def test_keywords_are_combined(patches):
    event = Patch.process(
        "https://highape.com/e", {"keywords": ["ZED", "HIGHAPE", "A"]}
    )
    assert event["keywords"] == ["A", "HIGHAPE", "ZED"]
    event = Patch.process("https://highape.com/e", {"keywords": {"content": "x"}})
    assert event["keywords"] == ["HIGHAPE"]
    assert get_patch("https://highape.com/e")["keywords"] == ["HIGHAPE"]


def test_patch_without_keywords(patches):
    event = Patch.process("https://tonight.is/e", {"keywords": ["TONIGHT"]})
    assert event == {"organizer": {"name": "Tonight"}, "keywords": ["TONIGHT"]}
