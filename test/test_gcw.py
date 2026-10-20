import datetime
from pathlib import Path
from types import SimpleNamespace

from src.sources import gcw

HOME = (Path(__file__).parent / "fixtures/gcw/home.html").read_text()
FORMS = {
    "https://forms.gle/kHG8hZ1zQPxYdVzF7": "1FAIpQLScMnKz_Dz4DjsC_6V88chpc-kR6Ah69OGwyLZxR4tO8d7ToCg",
    "https://forms.gle/cGAdYABwanqFBJmo9": "1FAIpQLSfBEtnySL8nk4box4kwpD5U-K3IhakSUADZPXQkXXQA5aLMFw",
    "https://forms.gle/aYNdytpyNiDNFHgeA": "1FAIpQLScPG6LXfHH78cXsgzOmw0Zhy4Lzt1XcCkaz2eX-XzNg1S1PHA",
}
MG_ROAD = "https://docs.google.com/forms/d/e/1FAIpQLScMnKz_Dz4DjsC_6V88chpc-kR6Ah69OGwyLZxR4tO8d7ToCg/viewform"


def serve(monkeypatch, *edits, now=(2026, 10, 20)):
    html = HOME
    for old, new in edits:
        assert old in html
        html = html.replace(old, new, 1)

    def get(url, headers=None, timeout=None):
        assert url == gcw.BASE and headers == gcw.USER_AGENT_HEADERS
        return SimpleNamespace(text=html)

    def head(url, headers=None, timeout=None, allow_redirects=True):
        assert not allow_redirects
        location = f"https://docs.google.com/forms/d/e/{FORMS[url]}/viewform?usp=send_form"
        return SimpleNamespace(headers={"location": location})

    class Fixed(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(*now, tzinfo=tz)

    monkeypatch.setattr(gcw, "datetime", SimpleNamespace(datetime=Fixed))
    monkeypatch.setattr(gcw, "get_cached_session", lambda: SimpleNamespace(get=get, head=head))


def test_walks_link_their_full_google_form(monkeypatch):
    serve(monkeypatch)
    walks = gcw.events()
    assert [w["name"] for w in walks] == ["Trees on Parade", "Botany in the Bazaar", "Green by Design"]
    walk = walks[0]
    assert walk["url"] == walk["offers"]["url"] == MG_ROAD
    assert walk["identifier"] == "gcw.2026-11-01"
    assert walk["startDate"] == "2026-11-01T07:30:00+05:30"
    assert walk["image"] == ["https://gardencitywalks.com/images/GCW_MGRoad19Oct.jpg"]
    assert walk["organizer"] == {
        "@type": "Organization",
        "name": "Garden City Walks",
        "url": "https://gardencitywalks.com/",
    }


def test_child_price_goes_in_the_description(monkeypatch):
    serve(monkeypatch)
    walk = gcw.events()[0]
    assert walk["offers"]["price"] == "1100"
    assert walk["description"].endswith(
        "with trees as our guides.\n\nPrice: ₹1100 for adults, free for kids under 10, "
        "half price for kids 10-15. "
        "Inclusions: Coffee, snacks and a keepsake."
    )


def test_past_walks_are_skipped(monkeypatch, capsys):
    serve(monkeypatch, now=(2026, 11, 20))
    assert [w["name"] for w in gcw.events()] == ["Green by Design"]
    assert "[GCW] Event in past: Trees on Parade" in capsys.readouterr().out


def test_walk_without_a_card_is_skipped(monkeypatch, capsys):
    serve(monkeypatch, ("<h3>Green by Design</h3>", "<h3>Green by Design II</h3>"))
    assert len(gcw.events()) == 2
    assert "[GCW] No booking card for Green by Design" in capsys.readouterr().out
