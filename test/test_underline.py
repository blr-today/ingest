import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from src.sources import underline
from src.sources.underline import event_links, post_text, ticket_offers

FIXTURES = Path(__file__).parent / "fixtures/underline"
POP_QUIZ = "https://district.in/pop-culture-quiz-by-calm-your-wits-quizzing-oct11-2026/event"


def post(id):
    return json.loads((FIXTURES / f"post-{id}.json").read_text())


class FakeSession:
    def __init__(self, redirects=None):
        self.redirects = redirects or {}
        self.requested = []

    def get(self, url, headers=None, timeout=None):
        self.requested.append(url)
        if url.startswith(underline.SITE_URL + "/posts/"):
            path = FIXTURES / ("post-" + url.split("/")[-1])
            if not path.exists():
                return SimpleNamespace(status_code=404)
            return SimpleNamespace(status_code=200, json=lambda: json.loads(path.read_text()))
        text = (FIXTURES / "district-pop-culture-quiz.html").read_text() if url == POP_QUIZ else "<html></html>"
        return SimpleNamespace(url=self.redirects.get(url, url), text=text)


def test_post_text_drops_event_block():
    text = post_text(post(1021)["cooked"])
    assert text.startswith("Is your Instagram screentime begging for overtime pay?")
    assert "discourse-post-event" not in text
    assert "\n\n\n" not in text


def test_links_skip_social_and_anchors():
    event = {"url": POP_QUIZ, "location": None}
    assert event_links(FakeSession(), event, post(1021)["cooked"]) == [POP_QUIZ]


def test_links_from_location_and_post():
    session = FakeSession()
    event = {"url": None, "location": "https://www.district.in/indiewebclub-meetup/event"}
    links = event_links(session, event, post(1040)["cooked"])
    assert links == [
        "https://www.district.in/indiewebclub-meetup/event",
        "https://indieweb.org/Homebrew_Website_Club",
        "https://indieweb.org/silos",
        "https://blr.indiewebclub.org",
    ]
    assert "https://at.underline.center/indiewebclub-whatsapp" in session.requested


def test_short_links_are_resolved():
    session = FakeSession({"https://link.underline.center/quiz": POP_QUIZ})
    links = event_links(session, {"url": "https://link.underline.center/quiz tickets"}, "")
    assert links == [POP_QUIZ]


def test_ticket_offers_match_start():
    offers = ticket_offers(FakeSession(), POP_QUIZ, "2026-10-11T18:30:00.000+05:30")
    assert offers["lowPrice"] == 399
    assert offers["offers"][0]["name"] == "Regular Ticket"


def test_ticket_offers_ignore_other_shows():
    assert ticket_offers(FakeSession(), POP_QUIZ, "2026-10-18T18:30:00.000+05:30") is None
    assert ticket_offers(FakeSession(), "https://district.in/other/event", "2026-10-11T18:30:00+05:30") is None


def test_main_enriches_events(monkeypatch, tmp_path):
    path = tmp_path / "underline.json"
    shutil.copy(FIXTURES / "events.json", path)
    data = json.loads(path.read_text())
    data["events"][1]["image_upload"] = None
    expired = dict(data["events"][0], is_expired=True)
    missing = dict(data["events"][0], post={"id": 1})
    data["events"] += [expired, missing]
    path.write_text(json.dumps(data))
    monkeypatch.setattr(underline, "get_cached_session", FakeSession)
    underline.main(path)
    quiz, ninjas, iwc, expired, missing = json.loads(path.read_text())["events"]
    assert quiz["description"].startswith("Is your Instagram screentime")
    assert quiz["links"] == [POP_QUIZ]
    assert quiz["offers"]["lowPrice"] == 399
    assert iwc["post"]["topic"]["slug"] == "indiewebclub-35"
    assert iwc["offers"] is None
    assert ninjas["links"] == ["https://district.in/folding-ninjas-with-roligami/event"]
    assert ninjas["image_upload"]["url"].endswith("/original/1X/49f160d758e3e619005b68de67f09b1ba365500f.jpeg")
    assert "links" not in expired and "links" not in missing
