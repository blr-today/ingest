import datetime
import json
import os
import sqlite3
import sys

from src.common.tz import IST

USAGE = "Usage: python -m src.carry <previous events.db> TAG1,TAG2"


def keywords(event):
    k = event.get("keywords") or []
    k = k.split(",") if isinstance(k, str) else k
    return {str(x).strip() for x in k if isinstance(x, str)}


def ends(event):
    """When the event is over, or None when it has no readable date"""
    value = str(event.get("endDate") or event.get("startDate") or "")
    try:
        moment = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    if len(value) <= 10:
        moment += datetime.timedelta(days=1)
    return moment if moment.tzinfo else moment.replace(tzinfo=IST)


def missing(db, tags):
    found = set()
    for (ej,) in db.execute("SELECT event_json FROM events"):
        found |= keywords(json.loads(ej)) & tags
    return tags - found


def carry(previous, tags, now=None, db_path="events.db"):
    """Copies upcoming events with any tag this build lacks from an older events.db"""
    now = now or datetime.datetime.now(IST)
    db = sqlite3.connect(db_path)
    lost = missing(db, tags)
    if not lost or not os.path.exists(previous):
        return lost, 0
    have = {url for (url,) in db.execute("SELECT url FROM events")}
    rows = []
    for url, ej in sqlite3.connect(previous).execute("SELECT url, event_json FROM events"):
        event = json.loads(ej)
        end = ends(event)
        if url not in have and keywords(event) & lost and end and end > now:
            rows.append((url, ej))
            have.add(url)
    db.executemany("INSERT INTO events (url, event_json) VALUES (?, ?)", rows)
    db.commit()
    return lost, len(rows)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(USAGE)
    tags = {t.strip() for t in sys.argv[2].split(",") if t.strip()}
    lost, count = carry(sys.argv[1], tags)
    for tag in sorted(lost):
        print(f"[CARRY] no {tag} events in this build")
    print(f"[CARRY] {count} upcoming events from {sys.argv[1]}")
