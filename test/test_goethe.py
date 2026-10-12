import datetime
import json
from pathlib import Path

from src.sources import goethe
from src.sources.goethe import fetch_events, get_event_details, get_event_type, make_event

FIXTURES = Path(__file__).parent / "fixtures" / "goethe"
LIST_URL = "https://www.goethe.de/rest/objeventcalendarRedesign/events/fetchEvents"
EVENT_URL = "https://www.goethe.de/ins/in/en/ver.cfm?event_id=27317867"


class FakeResponse:
    def __init__(self, text):
        self.text = text

    def json(self):
        return json.loads(self.text)


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.params = None

    def get(self, url, params=None):
        if params:
            self.params = params
        return FakeResponse(self.pages[url])


def session(listing="events.json", page=None):
    page = page or (FIXTURES / "event.html").read_text()
    return FakeSession({LIST_URL: (FIXTURES / listing).read_text(), EVENT_URL: page})


def item():
    return json.loads((FIXTURES / "events.json").read_text())["eventItems"][0]


def test_event_type_mapping():
    assert get_event_type("Film", "") == "ScreeningEvent"
    assert get_event_type("Other", "Jazz Music Night") == "MusicEvent"
    assert get_event_type("Workshop", "") == "EducationEvent"
    assert get_event_type("Call for Applications", "") is None
    assert get_event_type("Performance", "AHA! Theatre for Children Festival ") == "Event"


def test_event_page_details():
    details = get_event_details(session(), EVENT_URL)
    assert details["description"].startswith("We are happy to presentThe Day my Father became a Bush")
    assert details["image"].startswith("https://www.goethe.de/resources/files/png214/")
    assert details["location"] == {
        "@type": "Place",
        "name": "Ranga Shankara",
        "address": "No. 36/2, 8th Cross Road, JP Nagar, 2nd Phase, Bangalore 560078, India",
    }
    assert details["offers"] == {}


def test_institute_events_use_its_address():
    page = (FIXTURES / "event.html").read_text().replace("Ranga Shankara, Bangalore", "Goethe-Institut Bangalore")
    location = get_event_details(session(page=page), EVENT_URL)["location"]
    assert location["name"] == "Goethe-Institut"
    assert location["address"] == "716, CMH Road, Indiranagar 1st Stage, Bangalore"


def test_make_event():
    event = make_event(session(), item())
    assert event["name"] == "The day my father became a bush..."
    assert event["@type"] == "Event"
    assert event["url"] == EVENT_URL
    assert event["startDate"] == "2026-07-25T19:30:00"
    assert event["endDate"] == "2026-07-25T21:30:00"
    assert event["keywords"] == ["GOETHE", "AHA! Theatre for Children Festival ", "Dance and Theatre", "Children and youth theatre"]
    assert event["location"]["name"] == "Ranga Shankara"
    assert event["offers"] == {"price": "Sold out", "priceCurrency": "INR"}


def test_registration_link_goes_into_offers():
    raw = dict(item(), registration_link_url="https://example.org/register", price=None)
    assert make_event(session(), raw)["offers"] == {"url": "https://example.org/register"}


def test_fetch_events_filters_bangalore(monkeypatch):
    fake = session()
    monkeypatch.setattr(goethe, "get_cached_session", lambda: fake)
    [event] = fetch_events()
    assert event["url"] == EVENT_URL
    assert json.loads(fake.params["filterData"])["adress_IDtxt"] == "Bangalore"


def test_fetch_events_drops_non_events(monkeypatch):
    fake = session()
    listing = json.loads((FIXTURES / "events.json").read_text())
    listing["eventItems"][0]["event_type"] = "Call for Applications"
    fake.pages[LIST_URL] = json.dumps(listing)
    monkeypatch.setattr(goethe, "get_cached_session", lambda: fake)
    assert fetch_events() == []


def test_empty_calendar(monkeypatch):
    monkeypatch.setattr(goethe, "get_cached_session", lambda: session("empty.json"))
    assert fetch_events() == []


def test_end_time_from_listing():
    assert make_event(session(), dict(item(), time_end_txt="8:20 PM"))["endDate"] == "2026-07-25T20:20:00"
    assert make_event(session(), dict(item(), time_end_txt=""))["endDate"] == "2026-07-25T21:30:00"


def test_empty_price_is_free():
    assert make_event(session(), dict(item(), price=""))["isAccessibleForFree"] is True
    assert make_event(session(), dict(item(), price=0))["isAccessibleForFree"] is True
    assert "isAccessibleForFree" not in make_event(session(), dict(item(), price=None))


def test_long_events_are_dropped(monkeypatch):
    long = item() | {"date_end_full": "2026-08-05 00:00:00.0", "time_end_txt": ""}
    event = make_event(session(), long)
    assert event["endDate"] == "2026-08-05T21:30:00"
    assert event["@type"] is None


def test_unknown_end_fields_are_logged(capsys):
    make_event(session(), item() | {"enddate": "2026-08-05"})
    assert "Unhandled end fields: ['enddate']" in capsys.readouterr().out
