from processors.eventtype import EventType


def kind(name, keywords=(), description="", type_="Event"):
    event = {
        "@type": type_,
        "name": name,
        "keywords": list(keywords),
        "description": description,
    }
    return EventType.process("u", event)["@type"]


def test_names():
    assert kind("Flour Power: A Kids Cookie Workshop") == "ChildrensEvent"
    assert kind("Long Story Short - 5 Comic Shorts. 1 Fun Play.") == "TheaterEvent"
    assert kind("Toffee & Talk Book Club Meet-Up") == "LiteraryEvent"
    assert kind("Roast Tank - India's First Founders Roast Show") == "ComedyEvent"
    assert kind("Startup Founders Meetup") == "BusinessEvent"
    assert kind("Kombucha Tasting for Nerds") == "FoodEvent"
    assert kind("Heritage walk") == "Event"


def test_keywords_and_talks():
    assert kind("Ameeras", ["Music"]) == "MusicEvent"
    assert (
        kind("Pomp and Circumstance", ["Music"], "This talk uncovers a life")
        == "EducationEvent"
    )


def test_specific_types_are_kept():
    assert kind("Kids Workshop", type_="LiteraryEvent") == "LiteraryEvent"


def test_descriptions():
    hands_on = "In this hands-on workshop, you will make a puzzle"
    assert kind("Laser Cut Puzzles", description=hands_on) == "EducationEvent"
    assert (
        kind("Beyond the Buzz", description="This panel discussion examines")
        == "EducationEvent"
    )
    assert kind("Dakshin Diaries", description="this concert explores") == "MusicEvent"
