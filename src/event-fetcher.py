import extruct
from requests_cache import CachedSession
from datetime import timedelta
from w3lib.html import get_base_url
import sqlite3
import json

EVENT_JSON_FILES = [
    'out/bic.json',
    'out/sofar.json',
    'out/scigalleryblr.json',
    'out/sumukha.json',
    'out/bluetokai.json',
    'out/champaca.json',
    'out/gullytours.json',
    'out/mapindia.json',
]

KNOWN_EVENT_TYPES = [
    "Event",
    "BusinessEvent",
    "ChildrensEvent",
    "ComedyEvent",
    "CourseInstance",
    "DanceEvent",
    "DeliveryEvent",
    "EducationEvent",
    "EventSeries",
    "ExhibitionEvent",
    "Festival",
    "FoodEvent",
    "Hackathon",
    "LiteraryEvent",
    "MusicEvent",
    "PublicationEvent",
    "SaleEvent",
    "ScreeningEvent",
    "SocialEvent",
    "SportsEvent",
    "TheaterEvent",
    "VisualArtsEvent",
]

URL_FILES = [
    "out/allevents.txt",
    "out/bhaagoindia.txt",
    "out/highape.txt",
    "out/insider.txt",
    "out/mmb.txt",
]

def get_local_events(files):
    for i in files:
        with open(i, "r") as f:
            data = json.load(f)
            for event in data:
                yield (event['url'], event)

def get_events(s):
    for i in URL_FILES:
        with open(i, "r") as f:
            urls = f.readlines()
            for url in urls:
                url = url.strip()
                if url:
                    r = s.get(url)
                    base_url = get_base_url(r.text, r.url)
                    data = extruct.extract(
                        r.text, base_url=base_url, syntaxes=["json-ld"]
                    )

                    def find_event(l):
                        for d in l:
                            if d.get("@type") in KNOWN_EVENT_TYPES:
                                return (url, d)

                    m = None
                    for x in data["json-ld"]:
                        if x.get('@graph'):
                            m = m or find_event(x['@graph'])
                    m = m or find_event(data["json-ld"])
                    if m:
                        if m[1].get('LOCATION'):
                            m[1]['location'] = m[1].pop('LOCATION')
                        yield m
                    else:
                        print(f"Could not find event in {url}")

def insert_event_json(conn, url, event_json):
    d = json.dumps(event_json)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO events (url, event_json) VALUES (?, ?)', (url, d))

def create_events_table():
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            url TEXT UNIQUE,
            event_json TEXT
        );
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    create_events_table()
    session = CachedSession(
        "event-fetcher-cache",
        expire_after=timedelta(days=1),
        stale_if_error=True,
        use_cache_dir=True,
        cache_control=False,
    )
    conn = sqlite3.connect('events.db')
    i = 0
    for (url, d) in get_events(session):
        insert_event_json(conn, url, d)
        i+=1
        if i %10 == 0:
            conn.commit()

    for (url, d) in get_local_events(EVENT_JSON_FILES):
        insert_event_json(conn, url, d)
        print(url)
        i+=1
        if i %10 == 0:
            conn.commit()
    conn.commit()
    conn.close()