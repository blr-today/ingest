import json
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

# Lower rank wins; organiser sites beat aggregators that relist their events
AGGREGATORS = [
    "puttingscene.com",
    "urbanaut.app",
    "district.in",
    "skillboxes.com",
    "highape.com",
    "allevents.in",
]
ALWAYS_MERGE = ["improv lore"]


def rank(url):
    domain = urlparse(url).netloc.removeprefix("www.")
    return AGGREGATORS.index(domain) + 1 if domain in AGGREGATORS else 0


def normalize(text):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def core_title(name):
    return normalize(re.split(r"\s*[-|:–]\s+|\s+by\s+", name, maxsplit=1)[0])


def text_of(event, key):
    value = event.get(key)
    if isinstance(value, dict):
        return value.get("name") or ""
    return value if isinstance(value, str) else ""


def is_duplicate(a, b):
    host = (text_of(a, "name") + text_of(a, "organizer")).lower()
    other = (text_of(b, "name") + text_of(b, "organizer")).lower()
    if any(n in host and n in other for n in ALWAYS_MERGE):
        return True
    x, y = sorted(
        [core_title(a.get("name", "")), core_title(b.get("name", ""))], key=len
    )
    if not x:
        return False
    return x == y or (len(x.split()) >= 3 and y.startswith(x + " "))


def merge_keywords(kept, dropped):
    keywords = []
    for event in (kept, dropped):
        k = event.get("keywords", [])
        keywords += [s.strip() for s in k.split(",")] if isinstance(k, str) else k
    kept["keywords"] = list(
        dict.fromkeys(k for k in keywords if isinstance(k, str) and k)
    )


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
            match = next((k for k in kept if is_duplicate(k[2], row[2])), None)
            if not match:
                kept.append(row)
                continue
            merge_keywords(match[2], row[2])
            merged[match[0]] = match[2]
            conn.execute("DELETE FROM events WHERE rowid = ?", (row[0],))
            print(f"[DEDUP] {row[1]} -> {match[1]}")
            removed += 1
        for rowid, event in merged.items():
            conn.execute(
                "UPDATE events SET event_json = ? WHERE rowid = ?",
                (json.dumps(event, ensure_ascii=False), rowid),
            )
    conn.commit()
    print(f"[DEDUP] Removed {removed} duplicate events")


if __name__ == "__main__":
    dedup()
