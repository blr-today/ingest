import calendar
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qs, urljoin, urlparse

import cleanurl
from bs4 import BeautifulSoup
from common import maps
from common.session import get_cached_session
from common.jev import (
    MIN_CONFIDENCE,
    ask as ask_jev,
    clock,
    end_clock,
    pick,
    time_questions,
    value,
)
from common.tz import IST
from typesafe_sdk import Noul, TypeSafeClient

FEED = "https://brokebibliophilesbangalore.substack.com/feed"
POSTS = 2
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"
BLOCKS = ["p", "li", "h1", "h2", "h3"]
MONTHS = {str(m): calendar.month_name[m] for m in range(1, 13)}
NUMBER_RE = re.compile(r"\d[\d,]*")
EMOJI_RE = re.compile("[\U0001f300-\U0001faff☀-➿|]")
LABEL_RE = re.compile(
    r"^(when|where|venue|location|date and time|date|time|meetup)\s*[:?\-–]\s*",
    re.IGNORECASE,
)
FILLER_RE = re.compile(r"^(as always|as usual|once again)\s*,\s*", re.IGNORECASE)
URL_RE = re.compile(r"https?://\S+")
SKIP_HOSTS = ("substack.com", "substackcdn.com")
MAPS_RE = re.compile(
    r"^https?://((www\.)?google\.[a-z.]+/maps|maps\.google\.|maps\.app\.goo\.gl/|goo\.gl/maps/)"
)
ORGANIZER = {
    "@type": "Organization",
    "name": "Broke Bibliophiles Bangalore",
    "url": "https://brokebibliophilesbangalore.substack.com",
}


def log(*args):
    print("[BBB]", *args, file=sys.stderr)


def unique(items):
    return list(dict.fromkeys(i for i in items if i))


def segments(blocks):
    lines = (URL_RE.sub("", line) for block in blocks for line in block.splitlines())
    parts = (
        p.strip(" .,:-–")
        for line in lines
        for part in EMOJI_RE.split(line)
        for p in part.split(" - ")
    )
    parts = (FILLER_RE.sub("", LABEL_RE.sub("", p)).strip() for p in parts)
    return unique(p for p in parts if 3 <= len(p) <= 100)


def amounts(text):
    # Fees are never below 50 or above 5000, which also skips times and dates
    numbers = (m.group(0) for m in NUMBER_RE.finditer(text))
    return unique(n for n in numbers if 50 < int(n.replace(",", "")) < 5000)


def resolve(session, url):
    for _ in range(5):
        res = session.get(url, allow_redirects=False, timeout=30)
        if res.status_code not in (301, 302, 303, 307, 308):
            break
        url = urljoin(url, res.headers["location"])
        if urlparse(url).hostname == "consent.google.com":
            url = parse_qs(urlparse(url).query)["continue"][0]
            break
    result = cleanurl.cleanurl(url, respect_semantics=True)
    return result.url if result else url


def links(session, soup):
    hrefs = unique(a.get("href") for a in soup.find_all("a"))
    hrefs = [
        h for h in hrefs if h.startswith("http") and not any(s in h for s in SKIP_HOSTS)
    ]
    return {h: resolve(session, h) for h in hrefs}


def ask(client, post):
    s, year = post["segments"], date.today().year
    asks = {
        "event": Noul(
            instructions="Does this post announce a specific event, such as a book club "
            "meetup, that readers can attend on a stated date?"
        ),
        "has_fee": Noul(instructions="Does attending the announced event cost money?"),
        "month": pick("Which month is the announced event held in?", MONTHS),
        "day": pick(
            "Which day of the month is the announced event held on?",
            [str(d) for d in range(1, 32)],
        ),
        "year": pick(
            "Which year is the announced event held in?", [str(year), str(year + 1)]
        ),
        "venue": pick(
            "Which of these names the venue of the announced event?",
            unique(post["bold"] + s),
        ),
        "name": pick(
            "Which of these is the short name of the announced event?",
            unique([post["title"]] + post["bold"]),
        ),
        "fee": pick(
            "Which number is the fee in rupees to attend the announced event?",
            post["amounts"],
        ),
        "rsvp": pick(
            "Which link do attendees use to RSVP or register for the announced event?",
            [h for h in post["links"] if h not in post["maps"]],
        ),
        "map": pick(
            "Which map link shows the venue of the announced event?",
            {h: post["links"][h] for h in post["maps"]}
            if len(post["maps"]) > 1
            else {},
        ),
    } | time_questions("the announced event")
    state = {
        "title": post["title"],
        "published": post["published"].isoformat(),
        "text": post["text"],
    }
    return ask_jev(client, state, asks)


def event_date(picks, published):
    month, day = value(picks, "month"), value(picks, "day")
    if not month or not day:
        return None
    year = int(value(picks, "year") or published.year)
    when = date(year, int(month), int(day))
    if not value(picks, "year") and when < published:
        when = when.replace(year=year + 1)
    return when


def place(post, picks):
    venue = value(picks, "venue")
    if not venue:
        return None
    location = {"@type": "Place", "name": venue, "address": f"{venue}, Bengaluru"}
    link = post["maps"][0] if len(post["maps"]) == 1 else value(picks, "map")
    found = maps.resolve(link) if link else None
    if found:
        address, lat, lng = found
        location["address"] = address
        location["geo"] = {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng}
    if link:
        location["hasMap"] = post["links"][link]
    return location


def name(text):
    return text if "bibliophiles" in text.lower() else f"{ORGANIZER['name']}: {text}"


def to_event(post, nouls, picks):
    day = event_date(picks, post["published"])
    if not day:
        return None
    start, end = clock(picks, "start"), end_clock(nouls, picks)
    event = {
        "@context": "https://schema.org",
        "@type": "LiteraryEvent",
        "name": name(value(picks, "name") or post["title"]),
        "url": post["url"],
        "description": post["text"],
        "startDate": datetime.combine(day, start).isoformat()
        if start
        else day.isoformat(),
        "organizer": ORGANIZER,
    }
    if end:
        event["endDate"] = datetime.combine(day, end).isoformat()
    if location := place(post, picks):
        event["location"] = location
    if post["image"]:
        event["image"] = post["image"]
    offer = {"@type": "Offer"}
    fee = value(picks, "fee")
    if fee and nouls["has_fee"] >= MIN_CONFIDENCE:
        offer |= {"price": fee.replace(",", ""), "priceCurrency": "INR"}
    if rsvp := value(picks, "rsvp"):
        offer["url"] = post["links"][rsvp]
    if len(offer) > 1:
        event["offers"] = offer
    return event


def read_posts(session):
    root = ET.fromstring(session.get(FEED, timeout=30).content)
    for item in root.findall("./channel/item")[:POSTS]:
        soup = BeautifulSoup(item.findtext(CONTENT) or "", "html.parser")
        bold = segments(
            t.get_text(" ", strip=True) for t in soup.find_all(["strong", "b", "em"])
        )
        for br in soup.find_all("br"):
            br.replace_with("\n")
        blocks = unique(
            re.sub(r"[ \t]+", " ", b.get_text()).strip() for b in soup.find_all(BLOCKS)
        )
        text = "\n\n".join(blocks).split("Thanks for reading")[0].strip()
        hrefs = links(session, soup)
        enclosure = item.find("enclosure")
        yield {
            "title": item.findtext("title").strip(),
            "url": item.findtext("link"),
            "published": parsedate_to_datetime(item.findtext("pubDate"))
            .astimezone(IST)
            .date(),
            "text": text,
            "segments": segments(text.split("\n\n")),
            "bold": bold,
            "amounts": amounts(text),
            "links": hrefs,
            "maps": [
                h for h, url in hrefs.items() if MAPS_RE.match(h) or MAPS_RE.match(url)
            ],
            "image": enclosure.get("url") if enclosure is not None else None,
        }


def main():
    session = get_cached_session()
    events = {}
    with TypeSafeClient() as client:
        for post in read_posts(session):
            nouls, picks = ask(client, post)
            log(post["title"], {k: f"{p:.2f}" for k, p in nouls.items()})
            log({k: f"{c} ({p:.2f})" for k, (c, p) in picks.items()})
            event = (
                to_event(post, nouls, picks)
                if nouls["event"] >= MIN_CONFIDENCE
                else None
            )
            if event and event["startDate"][:10] >= date.today().isoformat():
                # The feed is newest first, so a later post about the same day loses
                events.setdefault(event["startDate"][:10], event)
    with open("out/bbb.json", "w") as f:
        json.dump(list(events.values()), f, indent=2, ensure_ascii=False)
    log(len(events), "upcoming events")


if __name__ == "__main__":
    main()
