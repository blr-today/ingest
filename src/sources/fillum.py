import datetime
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..common import USER_AGENT_HEADERS
from ..common.session import get_cached_session
from ..common.tz import IST

BASE = "https://fillum.in/"
HOSTS = ["https://fillum.in/user/52"]


def fetch(session, url):
    html = session.get(url, headers=USER_AGENT_HEADERS, timeout=30).text
    return BeautifulSoup(html, "html.parser")


def text(node):
    return " ".join(node.get_text(" ").split()) if node else ""


def offer(session, url):
    price = fetch(session, url).find("input", attrs={"name": "productprice"})
    if not price:
        print(f"[FILLUM] No tickets on sale: {url}")
        return None
    amount = float(price["value"])
    return {
        "@type": "Offer",
        "price": int(amount) if amount.is_integer() else amount,
        "priceCurrency": "INR",
        "url": url,
        "availability": "https://schema.org/InStock",
    }


def screening(session, url, sid):
    page = fetch(session, url)
    title = page.find(id="filmtitlebox")
    movie = {"@type": "Movie", "name": text(title.find(id="filmtitletext"))}
    if director := title.find("i"):
        movie["director"] = {"@type": "Person", "name": text(director)}
    synopsis = page.find(id="filmheadersynopsis")
    # The page repeats this card's id in its other-screenings list, so take the first
    ticket = page.find(id=f"screeningbox{sid}").select_one("a.ticketbtn")
    tickets = ticket and offer(session, urljoin(BASE, ticket["href"]))
    return movie, synopsis.get_text().strip() if synopsis else "", tickets


def card_event(session, card):
    link = card.select_one(".scfilmname a")
    url = urljoin(BASE, link["href"])
    if "screeningcitybangalore" not in card["class"]:
        print(f"[FILLUM] Not in Bangalore: {url}")
        return None
    when = text(card.select_one(".scfilmname + div"))
    start = datetime.datetime.strptime(when, "%d %b, %Y · %I:%M %p").replace(tzinfo=IST)
    if start < datetime.datetime.now(IST):
        print(f"[FILLUM] Event in past: {url}")
        return None
    movie, synopsis, tickets = screening(session, url, card["id"].removeprefix("screeningbox"))
    note = text(card.select_one(".scdescription"))
    venue = text(card.select_one(".sclocation"))
    host = card.select_one(".schost a")
    poster = re.search(r"url\((.+?)\)", card.select_one(".screeningposter")["style"])
    event = {
        "@context": "https://schema.org",
        "@type": "ScreeningEvent",
        "name": text(link),
        "url": url,
        "startDate": start.isoformat(),
        "image": urljoin(BASE, poster[1]),
        "description": synopsis + (f"\n\n{note}" if note else ""),
        "location": {
            "@type": "Place",
            "name": venue,
            "address": f"{venue}, {text(card.select_one('.sccity'))}",
        },
        "organizer": {"@type": "Organization", "name": text(host), "url": urljoin(BASE, host["href"])},
        "workPresented": movie,
    }
    if tickets:
        event["offers"] = tickets
    return event


def host_events(session, url):
    print(f"[FILLUM] {url}")
    cards = fetch(session, url).select("div[id^=screeningbox]")
    upcoming = [c for c in cards if "gscreeningbox" in c["class"]]
    return [e for c in upcoming if (e := card_event(session, c))]


def events():
    session = get_cached_session()
    return [e for url in HOSTS for e in host_events(session, url)]
