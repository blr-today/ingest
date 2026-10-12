import datetime
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.common import icalendar
from src.sources import iiwc
from src.sources.iiwc import get_location, modify_event

ICS = Path(__file__).parent / "fixtures/iiwc/events.ics"


@pytest.fixture(autouse=True)
def frozen_now(monkeypatch):
    class Fixed(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.datetime(2026, 10, 12, tzinfo=tz)

    monkeypatch.setattr(icalendar, "datetime", SimpleNamespace(datetime=Fixed))


def events():
    return {e["name"]: modify_event(e) for e in icalendar.convert_ics_to_events(ICS)}


def test_category_types():
    by_name = events()
    assert by_name["“Re-claim Constitution” – Gallery Show"]["@type"] == "ExhibitionEvent"
    assert by_name["Lecture Program- Tribute to Dr. S K Kareem Khan"]["@type"] == "EducationEvent"
    assert by_name["Drama Program"]["@type"] == "TheaterEvent"
    assert by_name["Nrityaankur Academy Annual Day Celebrations"]["@type"] == "DanceEvent"


def test_cultural_program_guessed_from_name():
    event = events()["Sri M A Narasimhachar Music Foundation Presents Carnatic Vocal Concert"]
    assert event["@type"] == "MusicEvent"


def test_uncategorised_event_stays_generic():
    assert events()["Repair – Reuse Workshop by Saahas"]["@type"] == "Event"


@pytest.mark.parametrize(
    "name, title",
    [("ನಾಟಕ ಪ್ರದರ್ಶನ", "TheaterEvent"), ("Kavya Vachana", "LiteraryEvent"), ("Bharata Natya Recital", "DanceEvent")],
)
def test_name_patterns(name, title):
    assert modify_event({"@type": "Event", "name": name})["@type"] == title


def test_locations():
    by_name = events()
    gallery = by_name["“Re-claim Constitution” – Gallery Show"]["location"]
    assert gallery["name"] == "Art Gallery, Indian Institute of World Culture, Basavanagudi, Bengaluru"
    assert gallery["address"]["postalCode"] == "560004"
    hall = by_name["Drama Program"]["location"]
    assert hall["name"] == "Wadia Hall, Indian Institute of World Culture, Basavanagudi, Bengaluru"


def test_institute_and_empty_locations():
    expected = "Indian Institute of World Culture, Basavanagudi, Bengaluru"
    assert get_location("The Indian Institute of World Culture, Bangalore")["name"] == expected
    assert get_location("")["name"] == expected


def test_events_read_out_ics(monkeypatch, tmp_path):
    (tmp_path / "out").mkdir()
    shutil.copy(ICS, tmp_path / "out/iiwc.ics")
    monkeypatch.chdir(tmp_path)
    assert len(iiwc.events()) == 7
