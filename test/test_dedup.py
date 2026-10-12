from src.dedup import is_duplicate

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
