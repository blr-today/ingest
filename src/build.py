from common.remote import fetch_remote_events
import os
import sqlite3
import json
import sys
import glob


def insert_event_json(conn, url, event_json):
    d = json.dumps(event_json)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO events (url, event_json) VALUES (?, ?)", (url, d))


def create_events_table():
    conn = sqlite3.connect("events.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            url TEXT,
            event_json TEXT
        );
    """
    )
    conn.commit()
    conn.close()


def fetch_local_events(file_filter=None):
    for json_file in glob.glob("out/*.json"):
        # Remove .json extension
        basename = os.path.basename(json_file)[:-5]

        if file_filter and json_file != file_filter:
            continue
        with open(json_file, "r") as f:
            data = json.load(f)
            for event in data:
                keywords = event.get("keywords", [])
                if isinstance(keywords, str):
                    keywords = ", " + basename.upper() + ", " + keywords
                elif isinstance(keywords, list):
                    keywords = list(set([basename.upper()] + keywords))
                event["keywords"] = keywords
                if "url" in event:
                    yield (event["url"], event)
                else:
                    print(f"Event in {json_file} has no URL: {event}")


if __name__ == "__main__":
    f = None
    if len(sys.argv) > 1:
        f = sys.argv[1]
    create_events_table()

    conn = sqlite3.connect("events.db")
    i = 0
    for url, event in fetch_remote_events(f):
        insert_event_json(conn, url, event)
        i += 1
        if i % 10 == 0:
            conn.commit()

    for url, event in fetch_local_events(f):
        insert_event_json(conn, url, event)
        i += 1
        if i % 10 == 0:
            conn.commit()
    conn.commit()
    conn.close()
