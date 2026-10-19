import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from contextlib import closing
from urllib.parse import urlsplit

# These sources end their slugs in their own event id, like resin-jhumka-workshop-vv0tytlqlg
SLUG_ID_HOSTS = {"highape.com", "skillboxes.com", "indiarunning.com"}
TRACKING = {"ref", "fbclid"}


def slug(text):
    return re.sub(r"[^a-z0-9_]+", "-", text.lower()).strip("-")


def namespace(url):
    host = (urlsplit(url).hostname or "").removeprefix("www.")
    return ".".join(reversed(host.split(".")))


def upstream_key(url, event):
    """The source's own id for an event, else the most specific part of its URL"""
    ld = event.get("@id")
    if isinstance(ld, str) and "://" not in ld:
        local = ld.split("@")[0].rsplit(":", 1)[-1]
        if m := re.match(r"event_(\d+)", local) or re.match(r"(\d[^-]*)-", local):
            return m[1]
        if local:
            return local
    parts = urlsplit(url)
    name, has_value, value = parts.query.split("&")[0].partition("=")
    if parts.query and name not in TRACKING and not name.startswith("utm_"):
        return value if has_value else name
    # A dated fragment marks the occurrence, which the start time already does
    if parts.fragment and not re.match(r"\d{4}", parts.fragment):
        return parts.fragment.rsplit("-", 1)[-1]
    segment = parts.path.rstrip("/").rsplit("/", 1)[-1]
    if (parts.hostname or "").removeprefix("www.") in SLUG_ID_HOSTS:
        return re.split(r"[-_]", segment)[-1]
    return segment.removesuffix("-buy-tickets")


def occurs(event):
    return re.sub(r"[-:]", "", str(event.get("startDate", ""))[:16]).lower()


def venue(event):
    place = event.get("location")
    if isinstance(place, list):
        place = place[0] if place else None
    name = place.get("name") if isinstance(place, dict) else None
    # BookMyShow names venues like "URU Whitefield: Bengaluru"
    return slug(name.split(":")[0]) if isinstance(name, str) else ""


def more_than_once(keys):
    counts = Counter(keys)
    return [counts[k] > 1 for k in keys]


def assign_ids(rows):
    """Ids for (url, event_json) rows: the start time and venue join in only when needed"""
    events = [json.loads(raw) for _, raw in rows]
    ids = [
        f"{namespace(url)}.{slug(upstream_key(url, e)) or 'event'}"
        for (url, _), e in zip(rows, events)
    ]
    ids = [
        f"{i}.{occurs(e)}" if again else i
        for i, e, again in zip(ids, events, more_than_once(ids))
    ]
    ids = [
        f"{i}.{venue(e)}" if again and venue(e) else i
        for i, e, again in zip(ids, events, more_than_once(ids))
    ]
    # Rows that still share an id are numbered by content, so every build agrees
    groups = defaultdict(list)
    for n, (i, row) in enumerate(zip(ids, rows)):
        groups[i].append((row, n))
    for i, members in groups.items():
        for count, (_, n) in enumerate(sorted(members)[1:], start=2):
            ids[n] = f"{i}-{count}"
    return ids


def write_ids(db_path="events.db"):
    with closing(sqlite3.connect(db_path)) as conn:
        if "id" not in [c[1] for c in conn.execute("PRAGMA table_info(events)")]:
            conn.execute("ALTER TABLE events ADD COLUMN id TEXT")
        rows = conn.execute("SELECT rowid, url, event_json FROM events").fetchall()
        ids = assign_ids([(url, raw) for _, url, raw in rows])
        assert len(set(ids)) == len(ids), "event ids are not unique"
        conn.executemany(
            "UPDATE events SET id = ? WHERE rowid = ?",
            [(i, r[0]) for i, r in zip(ids, rows)],
        )
        conn.commit()
    print(f"Wrote {len(ids)} event ids")


if __name__ == "__main__":
    write_ids(*sys.argv[1:])
