from src.dedup import is_duplicate, name_session, same_session

STUDIO = {"@type": "Place", "name": "New York dance classes"}


def nydc(name, url):
    return {"name": name, "url": url, "location": STUDIO}


def test_one_studio_merges_same_style():
    a = nydc("Garba & Dandiya Dance Workshop @ NYDC", "https://highape.com/a")
    b = nydc("NYDC Garba and Dandiya Workshop for Beginners", "https://district.in/b")
    assert is_duplicate(a, b)


def test_one_studio_keeps_other_styles():
    a = nydc("Heels Dance Workshop for Beginners", "https://district.in/a")
    b = nydc("Lap Couple Dance Workshop For Beginner", "https://district.in/b")
    assert not is_duplicate(a, b)


def test_other_venues_need_matching_titles():
    a = {"name": "Garba Night", "url": "https://x.in/a", "location": {"name": "Hall"}}
    b = {
        "name": "Garba Workshop",
        "url": "https://y.in/b",
        "location": {"name": "Hall"},
    }
    assert not is_duplicate(a, b)


def listing(name, venue, lat, lng, keywords=()):
    return {
        "name": name,
        "url": f"https://www.district.in/events/{name.lower().replace(' ', '-')}",
        "organizer": {"name": "Getaway Technologies Private Limited"},
        "location": {"name": venue, "geo": {"latitude": lat, "longitude": lng}},
        "keywords": list(keywords),
    }


def test_one_host_session_merges_across_venue_names():
    a = listing(
        "Kintsugi Workshop in HSR Layout", "Tim Hortons India", 12.9120662, 77.6470938
    )
    b = listing("SIP and PAINT", "Tim Hortons | HSR, Bangalore", 12.9121, 77.647)
    assert same_session(a, b)


def test_session_needs_same_place_and_visibility():
    a = listing("Sip and Clay", "URU - JP Nagar", 12.9057826, 77.6011616)
    b = listing("Sip and Paint", "URU - Whitefield", 12.9613421, 77.7325235)
    c = listing(
        "Mafia Night", "URU - JP Nagar", 12.9057826, 77.6011616, ["LOW-QUALITY"]
    )
    assert not same_session(a, b)
    assert not same_session(a, c)


def test_session_name_lists_choices():
    event = {"name": "Sip and Clay", "description": "Bring a friend."}
    name_session(event, ["Sip and Clay", "Sip and Paint", "Kintsugi"])
    assert event["name"] == "Sip and Clay and 2 more"
    assert event["description"].startswith(
        "Choose from: Sip and Clay; Sip and Paint; Kintsugi."
    )
