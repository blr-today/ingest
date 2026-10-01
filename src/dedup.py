import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from urllib.parse import unquote, urlparse

# Mirrors calendar types: venues/organisers win, then aggregators, then curators
AGGREGATORS = [
    "district.in",
    "urbanaut.app",
    "allevents.in",
    "highape.com",
    "skillboxes.com",
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
    text = re.sub(r"['’]", "", text.lower())
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


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


def is_duplicate(a, b):
    if links(a) & links(b):
        return True
    host = (text_of(a, "name") + text_of(a, "organizer")).lower()
    other = (text_of(b, "name") + text_of(b, "organizer")).lower()
    if any(n in host and n in other for n in ALWAYS_MERGE):
        return True
    x, y = sorted(
        [core_title(a.get("name", "")), core_title(b.get("name", ""))], key=len
    )
    if not x:
        return False
    if normalize(a.get("name", "")) == normalize(b.get("name", "")):
        return True
    return x == y or (len(x.split()) >= 3 and y.startswith(x + " "))


def as_list(value):
    if isinstance(value, str):
        return [value]
    return value if isinstance(value, list) else []


def merge(kept, dropped, dropped_url):
    keywords = []
    for event in (kept, dropped):
        k = event.get("keywords", [])
        keywords += [s.strip() for s in k.split(",")] if isinstance(k, str) else k
    kept["keywords"] = list(
        dict.fromkeys(k for k in keywords if isinstance(k, str) and k)
    )
    same_as = (
        as_list(kept.get("sameAs")) + [dropped_url] + as_list(dropped.get("sameAs"))
    )
    kept["sameAs"] = list(dict.fromkeys(u for u in same_as if u != kept.get("url")))
    images = as_list(kept.get("image")) + as_list(dropped.get("image"))
    if images and all(isinstance(i, str) for i in images):
        kept["image"] = list(dict.fromkeys(images))
    fill(kept, dropped)


def is_empty(value):
    return value is None or value == "" or value == [] or value == {}


def fill(kept, other):
    for key, value in other.items():
        if is_empty(value):
            continue
        if key not in kept or is_empty(kept[key]):
            kept[key] = value
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
        groups[start].append([rowid, url, event])

    removed = 0
    for events in groups.values():
        events.sort(key=lambda e: (rank(e[1]), e[0]))
        kept, merged = [], {}
        for row in events:
            # A site listing two events at one time means two different events
            match = next(
                (
                    k
                    for k in kept
                    if domain(k[1]) != domain(row[1]) and is_duplicate(k[2], row[2])
                ),
                None,
            )
            if not match:
                kept.append(row)
                continue
            merge(match[2], row[2], row[1])
            merged[match[0]] = match[2]
            conn.execute("DELETE FROM events WHERE rowid = ?", (row[0],))
            print(f"[DEDUP] {row[1]} -> {match[1]}")
            removed += 1
        # Curators point at the organiser's own page, a better main link
        for rowid, _, event in kept:
            if promote(event):
                merged[rowid] = event
        for rowid, event in merged.items():
            conn.execute(
                "UPDATE events SET event_json = ? WHERE rowid = ?",
                (json.dumps(event, ensure_ascii=False), rowid),
            )
    conn.commit()
    print(f"[DEDUP] Removed {removed} duplicate events")


if __name__ == "__main__":
    dedup()
