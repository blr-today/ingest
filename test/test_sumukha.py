import json
from datetime import datetime
from pathlib import Path

import sumukha
from common.tz import IST
from sumukha import extract_rsc_payload, fetch_exhibition_candidates, parse_date_range, parse_exhibition_page

FIXTURES = Path(__file__).parent / "fixtures" / "sumukha"
PAGE_URL = "https://sumukha.com/exhibitions/441"


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeSession:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        return FakeResponse(self.pages[url])


def frozen(monkeypatch, *args):
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(*args, tzinfo=IST)

    monkeypatch.setattr(sumukha, "datetime", FrozenDatetime)


def serve(monkeypatch, **pages):
    files = {"exhibitions": sumukha.EXHIBITIONS_URL, "441": PAGE_URL}
    text = {files[name]: (FIXTURES / f"{name}.html").read_text() for name in files}
    text.update(pages)
    monkeypatch.setattr(sumukha, "session", FakeSession(text))


def test_parse_date_range():
    start, end = parse_date_range("August 28, 2026 to October 02, 2026")
    assert start.isoformat() == "2026-08-28T00:00:00+05:30"
    assert end.isoformat() == "2026-10-02T00:00:00+05:30"
    start, end = parse_date_range("January 5, 2026")
    assert start == end
    assert parse_date_range("Coming soon") == (None, None)


def test_rsc_payload_joins_chunks():
    rsc = extract_rsc_payload((FIXTURES / "exhibitions.html").read_text())
    assert rsc.startswith('8:["$","$L12",null,{"exhibitions":[{"id":441')
    assert rsc.endswith("]}]\n")


def test_candidates_skip_long_past_exhibitions(monkeypatch):
    serve(monkeypatch)
    frozen(monkeypatch, 2026, 10, 4)
    assert [ex["id"] for ex in fetch_exhibition_candidates()] == [441]
    frozen(monkeypatch, 2026, 2, 20)
    assert [ex["id"] for ex in fetch_exhibition_candidates()] == [441, 440, 429]


def test_parses_exhibition_page(monkeypatch):
    serve(monkeypatch)
    frozen(monkeypatch, 2026, 10, 1)
    event = parse_exhibition_page(PAGE_URL, "441-whatsapp_image_2026_08_19_at_4_27_05_pm-07f6bdbb.jpg")
    assert event["@type"] == "ExhibitionEvent"
    assert event["name"] == "In Search of the Perfect Image"
    assert event["startDate"] == "2026-08-28T00:00:00+05:30"
    assert event["endDate"] == "2026-10-02T23:59:59+05:30"
    assert event["image"] == f"{sumukha.IMAGE_BASE}/441-whatsapp_image_2026_08_19_at_4_27_05_pm-07f6bdbb.jpg"
    assert event["description"].startswith("A solo show by G Ravinder Reddy\n\nRavinder Reddy is known for his heads.")
    assert event["location"]["name"] == "Gallery Sumukha"
    assert event["isAccessibleForFree"] is True


def test_ended_exhibition_is_dropped(monkeypatch):
    serve(monkeypatch)
    frozen(monkeypatch, 2026, 10, 3)
    assert parse_exhibition_page(PAGE_URL, None) is None


def test_page_without_subtitle_or_prose(monkeypatch):
    html = (FIXTURES / "441.html").read_text()
    html = html.replace('<p class="text-base text-gray-600 mb-3">A solo show by G Ravinder Reddy</p>', "")
    html = html.replace("prose", "notes")
    serve(monkeypatch, **{PAGE_URL: html})
    frozen(monkeypatch, 2026, 9, 1)
    event = parse_exhibition_page(PAGE_URL, "")
    assert event["description"] == ""
    assert event["image"] == ""


def test_malformed_pages_are_skipped(monkeypatch):
    html = (FIXTURES / "441.html").read_text()
    serve(monkeypatch, **{
        "no-header": "<html><body><h1>Gone</h1></body></html>",
        "no-title": html.replace("<h1", "<h2").replace("</h1>", "</h2>"),
        "no-dates": html.replace("August 28, 2026 to October 02, 2026", "Dates to be announced"),
        "bad-dates": html.replace("August 28, 2026", "Augst 28, 2026"),
    })
    frozen(monkeypatch, 2026, 9, 1)
    for url in ("no-header", "no-title", "no-dates", "bad-dates"):
        assert parse_exhibition_page(url, None) is None


def test_main_writes_current_exhibitions(monkeypatch, tmp_path):
    serve(monkeypatch)
    frozen(monkeypatch, 2026, 10, 1)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out").mkdir()
    sumukha.main()
    [event] = json.loads((tmp_path / "out" / "sumukha.json").read_text())
    assert event["url"] == PAGE_URL
