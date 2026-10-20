import datetime
import json

from bs4 import BeautifulSoup

from ..common import USER_AGENT_HEADERS
from ..common.session import get_cached_session
from ..common.tz import IST

BASE = "https://gardencitywalks.com/"


def text(node):
    return " ".join(node.get_text(" ").split()) if node else ""


def form_url(session, short):
    # Booking links are forms.gle redirects to the full Google Form
    r = session.head(short, headers=USER_AGENT_HEADERS, timeout=30, allow_redirects=False)
    return r.headers.get("location", short).split("?")[0]


def walk_cards(page):
    cards = {}
    for card in page.select("article.walk"):
        details = dict(zip(map(text, card.select("dt")), card.select("dd")))
        cards[text(card.find("h3"))] = {
            "book": card.select_one("a.walk-book")["href"],
            "price": text(details["Price"].select_one("span")),
            "inclusions": text(details.get("Inclusions")),
        }
    return cards


def make_event(session, walk, card, organizer):
    url = form_url(session, card["book"])
    notes = [f"Price: {card['price']}, free for kids under 10, half price for kids 10-15."]
    if card["inclusions"]:
        notes.append(f"Inclusions: {card['inclusions']}.")
    event = walk | {
        "@context": "https://schema.org",
        "identifier": "gcw." + walk["startDate"][:10],
        "url": url,
        "description": walk["description"] + "\n\n" + " ".join(notes),
        "organizer": organizer,
    }
    event["offers"] = walk["offers"] | {"url": url}
    return event


def events():
    session = get_cached_session()
    page = BeautifulSoup(session.get(BASE, headers=USER_AGENT_HEADERS, timeout=30).text, "html.parser")
    graph = json.loads(page.find("script", type="application/ld+json").string)["@graph"]
    org = next(n for n in graph if n["@type"] == "Organization")
    organizer = {"@type": "Organization", "name": org["name"], "url": org["url"]}
    cards = walk_cards(page)
    today = datetime.datetime.now(IST).isoformat()
    result = []
    for walk in (n for n in graph if n["@type"] == "Event"):
        if walk["name"] not in cards:
            print(f"[GCW] No booking card for {walk['name']}")
        elif walk["startDate"] < today:
            print(f"[GCW] Event in past: {walk['name']}")
        else:
            result.append(make_event(session, walk, cards[walk["name"]], organizer))
    return result
