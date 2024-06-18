import extruct
from requests_cache import CachedSession
from datetime import timedelta
from w3lib.html import get_base_url
import sqlite3
from bs4 import BeautifulSoup
import json
import sys
import os

LANGUAGE_MAP = {
    "English": "en",
    "Hindi": "hi",
    "Kannada": "kn",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Marathi": "mr",
    "Bengali": "bn",
    "Gujarati": "gu",
    "Punjabi": "pa",
    "Odia": "or",
    "Assamese": "as",
    "Urdu": "ur",
    "Sanskrit": "sa",
    "Nepali": "ne",
    "Sindhi": "sd",
}

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
    "out/skillboxes.txt",
    "out/creativemornings.txt",
    "out/together-buzz.txt"
]

def get_local_events(files, f):
    for i in files:
        if f and i!=f:
            continue
        patch = get_patch(i)
        if os.path.exists(i):
            with open(i, "r") as f:
                data = json.load(f)
                for event in data:
                    if patch:
                        patch.update(event)
                        event = patch
                    yield (event['url'], event)
        else:
            print(f"[ERROR] Missing {i}")

def get_events(s, f):
    for i in URL_FILES:
        if f and i!=f:
            continue
        with open(i, "r") as f:
            patch = get_patch(i)
            urls = f.readlines()
            for url in urls:
                url = url.strip()
                print(url)
                if url:
                    keywords = None
                    r = s.get(url)
                    base_url = get_base_url(r.text, r.url)
                    # extract the meta name="keywords" tag using bs4
                    soup = BeautifulSoup(r.text, "html.parser")
                    meta = soup.find("meta", attrs={"name": "keywords"})
                    if meta:
                        keywords = meta["content"]

                    if len(r.text) == 0:
                        break

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
                        if keywords:
                            if 'keywords' in m[1]:
                                # insider reports keywords as a dict (incorrectly) so we ignore and rewrite from meta tags
                                try:
                                    keywords = ",".join(set(m[1]['keywords'].split(",") + keywords.split(",")))
                                except:
                                    pass
                            m[1]['keywords'] = keywords

                        # These are workarounds for broken schema published by Insider
                        try:
                            if 'language' in m[1]['inLanguage']:
                                m[1]['inLanguage']['name'] = m[1]['inLanguage']['language']
                                m[1]['inLanguage']['alternateName'] = LANGUAGE_MAP.get(m[1]['inLanguage']['language'], 'und')
                                del m[1]['inLanguage']['language']
                        except:
                            pass
                        try:
                            if m1['typicalAgeRange']['@type'] == 'Age-Range':
                                m[1]['typicalAgeRange'] = m[1]['typicalAgeRange']['language']
                        except:
                            pass
                        if patch:
                            patch.update(m[1])
                            yield (m[0], patch)
                        else:
                            yield m
                    else:
                        print(f"Could not find event in {url}")

def insert_event_json(conn, url, event_json):
    d = json.dumps(event_json)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO events (url, event_json) VALUES (?, ?)', (url, d))

def get_patch(input_file):
    basename = os.path.splitext(os.path.basename(input_file))[0]
    patch = os.path.join("patch", basename + ".json")
    if os.path.exists(patch):
        with open(patch, 'r') as file:
            return json.load(file)

def create_events_table():
    conn = sqlite3.connect('events.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            url TEXT,
            event_json TEXT
        );
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    f = None
    if len(sys.argv) > 1:
        f = sys.argv[1]
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
    for (url, d) in get_events(session, f):
        insert_event_json(conn, url, d)
        i+=1
        if i %10 == 0:
            conn.commit()

    for (url, event) in get_local_events(EVENT_JSON_FILES, f):
        insert_event_json(conn, url, event)
        print(url)
        i+=1
        if i %10 == 0:
            conn.commit()
    conn.commit()
    conn.close()