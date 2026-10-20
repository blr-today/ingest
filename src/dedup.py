import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta
from urllib.parse import unquote, urlparse

from src.common.activities import EXCLUDE, TAGS
from src.processors.cost import TAGS as COST_TAGS, Cost, price

# Mirrors calendar types: venues/organisers win, then aggregators, then curators
AGGREGATORS = [
    "district.in",
    "urbanaut.app",
    "allevents.in",
    "highape.com",
    "skillboxes.com",
    "in.bookmyshow.com",
]
CURATORS = [
    "puttingscene.com",
    "indiarunning.com",
    "bhaagoindia.com",
    "bengalurusustainabilityforum.org",
    "tonight.is",
]
RANKED = AGGREGATORS + CURATORS
ALWAYS_MERGE = ["improv lore"]
FAR_KM = 2
NEAR = timedelta(minutes=30)
# One studio runs one class per slot, however many listings name it
ONE_ROOM = ["new york dance"]
GENERIC = {"a", "and", "at", "by", "for", "in", "the", "with", "dance", "dancing"}
GENERIC |= {"workshop", "workshops", "beginner", "beginners", "class", "classes"}
GENERIC |= {"nydc", "new", "york"}
SOCIAL = [
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "linktr.ee",
    "wa.me",
    "whatsapp.com",
    "forms.gle",
    "docs.google.com",
]


def domain(url):
    return urlparse(url).netloc.removeprefix("www.")


def rank(url):
    return RANKED.index(domain(url)) + 1 if domain(url) in RANKED else 0


def normalize(text):
    text = re.sub(r"['’]", "", text.lower()).replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def compact(name):
    # Listings split words differently, as in stand-up and standup
    return normalize(name).replace(" ", "")


def core_title(name):
    return normalize(re.split(r"\s*[-|:–]\s+|\s+by\s+", name, maxsplit=1)[0])


def text_of(event, key):
    value = event.get(key)
    if isinstance(value, dict):
        return value.get("name") or ""
    return value if isinstance(value, str) else ""


def links(event):
    urls = [event.get("url")] + as_list(event.get("sameAs"))
    return {
        re.sub(r"^https?://(www\.)?", "", unquote(u).lower()).rstrip("/")
        for u in urls
        if isinstance(u, str) and u
    }


def host(event):
    return " ".join(
        text_of(event, k) for k in ("name", "organizer", "location")
    ).lower()


def one_room(event):
    return any(n in host(event) for n in ONE_ROOM)


def styles(event):
    return set(normalize(text_of(event, "name")).split()) - GENERIC


def hidden(event):
    k = event.get("keywords", [])
    return bool(EXCLUDE & set(k.split(",") if isinstance(k, str) else k))


def activities(event):
    k = event.get("keywords", [])
    tags = set(k.split(",") if isinstance(k, str) else k)
    return {t for t in tags if t in TAGS and TAGS[t][0] is None}


def same_session(a, b):
    if hidden(a) != hidden(b):
        return False
    if same_lineup(a, b):
        return True
    # Aggregators let one host list each activity of a session as its own event
    if domain(a.get("url", "")) not in AGGREGATORS:
        return False
    if domain(a.get("url", "")) != domain(b.get("url", "")):
        return False
    # A venue's painting class and its dance class are not one session
    x, y = activities(a), activities(b)
    if x and y and not x & y:
        return False
    organizer = text_of(a, "organizer")
    return bool(organizer) and organizer == text_of(b, "organizer") and same_place(a, b)


def geo(event):
    place = event.get("location")
    point = place.get("geo") if isinstance(place, dict) else None
    try:
        return float(point["latitude"]), float(point["longitude"])
    except KeyError, TypeError, ValueError:
        return None


def far_apart(a, b):
    x, y = geo(a), geo(b)
    if not (x and y):
        return False
    north = (x[0] - y[0]) * 110.6
    east = (x[1] - y[1]) * 109.0
    return north * north + east * east > FAR_KM * FAR_KM


def same_place(a, b):
    if far_apart(a, b):
        return False
    venue = text_of(a, "location")
    if venue and venue == text_of(b, "location"):
        return True
    # Listings name one venue in several ways, so close points match too
    x, y = geo(a), geo(b)
    return bool(x and y) and abs(x[0] - y[0]) < 6e-4 and abs(x[1] - y[1]) < 6e-4


def lineup(event):
    value = event.get("performer")
    people = [value] if isinstance(value, (dict, str)) else as_list(value)
    names = (p.get("name") if isinstance(p, dict) else p for p in people)
    return {normalize(n) for n in names if isinstance(n, str)} - {"", "various artists"}


def same_lineup(a, b):
    # Clubs list one slot's lineup under several titles, and share comedians next door
    x, y = lineup(a), lineup(b)
    if not (x & y) or 2 * len(x & y) < min(len(x), len(y)):
        return False
    if domain(a.get("url", "")) != domain(b.get("url", "")):
        return same_place(a, b)
    venue = text_of(a, "location")
    return bool(venue) and venue == text_of(b, "location")


def name_session(event, names):
    event["name"] = f"{names[0]} and {len(names) - 1} more"
    choices = "Choose from: " + "; ".join(names) + "."
    event["description"] = "\n\n".join(
        filter(None, [choices, event.get("description")])
    )


def is_duplicate(a, b):
    # One BMS page lists every venue, so a shared link can still be far apart
    if far_apart(a, b):
        return False
    if links(a) & links(b):
        return True
    if any(n in host(a) and n in host(b) for n in ALWAYS_MERGE):
        return True
    if one_room(a) and one_room(b) and styles(a) & styles(b):
        return True
    x, y = sorted(
        [core_title(a.get("name", "")), core_title(b.get("name", ""))], key=len
    )
    if not x:
        return False
    if compact(a.get("name", "")) == compact(b.get("name", "")):
        return True
    if x.replace(" ", "") == y.replace(" ", ""):
        return True
    return len(x.split()) >= 3 and f" {x} " in f" {y} "


def as_list(value):
    if isinstance(value, str):
        return [value]
    return value if isinstance(value, list) else []


def offer_list(offers):
    if isinstance(offers, dict):
        return [offers]
    return (
        [o for o in offers if isinstance(o, dict)] if isinstance(offers, list) else []
    )


def combine_offers(kept, dropped):
    seen, offers = set(), []
    for offer in offer_list(kept.get("offers")) + offer_list(dropped.get("offers")):
        amount = price(offer)
        key = json.dumps(offer, sort_keys=True) if amount is None else amount
        if (key, offer.get("priceCurrency") or "INR") not in seen:
            seen.add((key, offer.get("priceCurrency") or "INR"))
            offers.append(offer)
    return offers


def merge(kept, dropped, dropped_url):
    # A specific type such as ScreeningEvent beats a plain Event
    if kept.get("@type") in (None, "Event") and isinstance(dropped.get("@type"), str):
        kept["@type"] = dropped["@type"]
    keywords = []
    for event in (kept, dropped):
        k = event.get("keywords", [])
        keywords += [s.strip() for s in k.split(",")] if isinstance(k, str) else k
    # One cost tag survives if the merged offers cannot price the event
    costs = [k for k in keywords if k in COST_TAGS]
    keywords = [k for k in keywords if k not in COST_TAGS or k == costs[0]]
    keywords = list(dict.fromkeys(k for k in keywords if isinstance(k, str) and k))
    same_as = (
        as_list(kept.get("sameAs")) + [dropped_url] + as_list(dropped.get("sameAs"))
    )
    same_as = list(dict.fromkeys(u for u in same_as if u != kept.get("url")))
    images = as_list(kept.get("image")) + as_list(dropped.get("image"))
    original = kept.get("offers")
    offers = combine_offers(kept, dropped)
    # An identifier names its own source's event, so it never moves to another
    fill(kept, {k: v for k, v in dropped.items() if k != "identifier"})
    kept["keywords"] = keywords
    kept["sameAs"] = same_as
    if images and all(isinstance(i, str) for i in images):
        kept["image"] = list(dict.fromkeys(images))
    # Both copies' tickets are kept, but only one per price
    if not offers:
        pass
    elif offers == offer_list(original):
        kept["offers"] = original
    elif offers == offer_list(dropped.get("offers")):
        kept["offers"] = dropped["offers"]
    elif offers:
        kept["offers"] = offers
    Cost.process(kept.get("url"), kept)


def is_empty(value):
    return value is None or value == "" or value == [] or value == {}


def fill(kept, other):
    for key, value in other.items():
        if is_empty(value):
            continue
        if key not in kept or is_empty(kept[key]):
            kept[key] = value
        elif isinstance(kept[key], list) and isinstance(value, list):
            kept[key] = kept[key] + [v for v in value if v not in kept[key]]
        elif (
            isinstance(kept[key], dict)
            and isinstance(value, dict)
            and kept[key].get("@type") == value.get("@type")
        ):
            fill(kept[key], value)


def promote(event):
    url = event.get("url", "")
    if domain(url) not in CURATORS:
        return False
    for link in as_list(event.get("sameAs")):
        if not isinstance(link, str) or not link.startswith("http"):
            continue
        host = domain(link)
        if host in RANKED:
            continue
        if any(host == s or host.endswith("." + s) for s in SOCIAL):
            continue
        event["url"] = link
        event["sameAs"] = [url] + [u for u in as_list(event["sameAs"]) if u != link]
        print(f"[DEDUP] {url} links to {link}")
        return True
    return False


def dedup(db_path="events.db"):
    conn = sqlite3.connect(db_path)
    groups = defaultdict(list)
    for rowid, url, event_json in conn.execute(
        "SELECT rowid, url, event_json FROM events"
    ):
        event = json.loads(event_json)
        try:
            start = datetime.fromisoformat(event["startDate"])
        except KeyError, TypeError, ValueError:
            continue
        if one_room(event):
            start = start.replace(minute=start.minute // 15 * 15, second=0)
        groups[start].append([rowid, url, event])

    removed = 0
    for events in groups.values():
        events.sort(key=lambda e: (rank(e[1]), e[0]))
        kept, merged, sessions = [], {}, {}
        for row in events:
            # A site listing two events at one time means two different events
            match = next(
                (
                    k
                    for k in kept
                    if (
                        domain(k[1]) != domain(row[1])
                        or one_room(k[2])
                        and one_room(row[2])
                        or same_lineup(k[2], row[2])
                    )
                    and is_duplicate(k[2], row[2])
                ),
                None,
            )
            session = not match and next(
                (
                    k
                    for k in kept
                    if same_session(k[2], row[2])
                ),
                None,
            )
            if session:
                names = sessions.setdefault(
                    session[0], [session[2].get("name", "").strip()]
                )
                names.append(row[2].get("name", "").strip())
                match = session
            if not match:
                kept.append(row)
                continue
            merge(match[2], row[2], row[1])
            merged[match[0]] = match[2]
            conn.execute("DELETE FROM events WHERE rowid = ?", (row[0],))
            print(f"[DEDUP] {row[1]} -> {match[1]}")
            removed += 1
        for rowid, names in sessions.items():
            name_session(merged[rowid], names)
        # Curators point at the organiser's own page, a better main link
        for rowid, _, event in kept:
            if promote(event):
                merged[rowid] = event
        for rowid, event in merged.items():
            conn.execute(
                "UPDATE events SET event_json = ? WHERE rowid = ?",
                (json.dumps(event, ensure_ascii=False), rowid),
            )
    removed += merge_near(conn)
    conn.commit()
    print(f"[DEDUP] Removed {removed} duplicate events")


def merge_near(conn):
    # A venue can list one show twice, minutes apart
    places = defaultdict(list)
    for rowid, url, event_json in conn.execute(
        "SELECT rowid, url, event_json FROM events"
    ):
        event = json.loads(event_json)
        try:
            start = datetime.fromisoformat(event["startDate"])
        except KeyError, TypeError, ValueError:
            continue
        if text_of(event, "location") and start.tzinfo and not one_room(event):
            places[text_of(event, "location")].append([start, rowid, url, event])
    removed = 0
    for rows in places.values():
        rows.sort(key=lambda r: (r[0], r[1]))
        kept = []
        for row in rows:
            match = next(
                (
                    k
                    for k in kept
                    if k[0] < row[0] <= k[0] + NEAR
                    and hidden(k[3]) == hidden(row[3])
                    and is_duplicate(k[3], row[3])
                ),
                None,
            )
            if not match:
                kept.append(row)
                continue
            merge(match[3], row[3], row[2])
            conn.execute(
                "UPDATE events SET event_json = ? WHERE rowid = ?",
                (json.dumps(match[3], ensure_ascii=False), match[1]),
            )
            conn.execute("DELETE FROM events WHERE rowid = ?", (row[1],))
            print(f"[DEDUP] {row[2]} -> {match[2]}")
            removed += 1
    return removed


if __name__ == "__main__":
    dedup()
