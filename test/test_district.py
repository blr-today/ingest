import json
from pathlib import Path

from src.processors.district import District

EVENT = json.loads((Path(__file__).parent / "fixtures/district/event.json").read_text())


def test_scraped_keywords_are_deduped():
    event = District.process(EVENT["url"], json.loads(json.dumps(EVENT)))
    assert sorted(event["keywords"].split(",")) == [
        " All",
        "Modular Type Workshop by A Letter Atelier",
    ]
    assert event["name"] == EVENT["name"]


def test_language_dict_gets_schema_names():
    event = {"inLanguage": {"@type": "Language", "language": "Kannada"}}
    assert District.process("u", event)["inLanguage"] == {
        "@type": "Language",
        "name": "Kannada",
        "alternateName": "kn",
    }
    event = {"inLanguage": {"language": "Klingon"}}
    assert District.process("u", event)["inLanguage"]["alternateName"] == "und"


def test_age_range_is_flattened():
    event = {"typicalAgeRange": {"@type": "Age-Range", "language": "18+"}}
    assert District.process("u", event)["typicalAgeRange"] == "18+"
    event = {"typicalAgeRange": "5-12", "inLanguage": "English"}
    assert District.process("u", dict(event)) == event


def test_keyword_dicts_are_left_alone():
    keywords = {"@type": "Description", "content": "Standup Comedy Special ,All"}
    assert District.process("u", {"keywords": keywords})["keywords"] is keywords


def test_odd_shapes_are_left_alone():
    for event in (
        {"inLanguage": None, "typicalAgeRange": None},
        {"inLanguage": "Sign language", "typicalAgeRange": ["18+"]},
        {"inLanguage": ["English"], "typicalAgeRange": {"@type": "Age-Range"}},
        {"keywords": ["A", "A"]},
    ):
        assert District.process("u", json.loads(json.dumps(event))) == event
