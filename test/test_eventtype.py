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


def test_food_making_is_food():
    event = {"@type": "Event", "name": "Learn Brahmi: a workshop and Mauryan Lunch"}
    EventType.process("u", event)
    assert event["@type"] == "FoodEvent"
    assert event["additionalType"] == ["https://schema.org/EducationEvent"]
    assert kind("Blackstratblues at Hamilton Cocktail Bar") == "Event"
    assert kind("Dandiya Night - Old Mill Brewing") == "Event"
    assert kind("Reformer Pilates X Matcha Making Workshop") == "FoodEvent"
    assert (
        kind("Pastry Making Workshop", description="this hands-on workshop")
        == "FoodEvent"
    )
    assert kind("Mixology Masterclass") == "FoodEvent"
    assert kind("Home Coffee Brewing Workshop") == "FoodEvent"
    assert kind("Crochet & Coffee Workshop") == "EducationEvent"
