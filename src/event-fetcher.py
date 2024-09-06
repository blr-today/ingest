from common.jsonld import JsonLdExtractor
import time
from common import USER_AGENT_HEADERS
from common.session import get_cached_session
from datetime import timedelta, datetime
from w3lib.html import get_base_url
import sqlite3
import datefinder
from bs4 import BeautifulSoup
from common.tz import IST
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
    # "Sanskrit": "sa",
    "Nepali": "ne",
    "Sindhi": "sd",
}

EVENT_JSON_FILES = [
    "out/bic.json",
    "out/sofar.json",
    "out/scigalleryblr.json",
    "out/sumukha.json",
    "out/bluetokai.json",
    "out/champaca.json",
    "out/gullytours.json",
    "out/mapindia.json",
    "out/adidas.json",
    "out/tonight.json",  # this includes duplicates to insider
    "out/trove.json",
    "out/aceofpubs.json",
    "out/atta_galatta.json",
    "out/urbanaut.json",
    "out/bengalurusustainabilityforum.json",
    "out/venn.json",  # this also has a lot of duplicates
    "out/te.json",
    "out/zomato.json",
    "out/underline.json",  # duplicates to insider
    "out/sis.json",
    "out/bcc.json",
    "out/tpcc.json",  # duplicates to underline and insider
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
    "out/together-buzz.txt",
    "out/koota.txt",
    "out/pumarun.txt",
]

IGNORED_EVENT_UIDS = ["60749-1718409600-1722470399@bangaloreinternationalcentre.org"]


def fix_online_schema(url, event):
    for x in ["startDate", "endDate"]:
        if x in event:
            # HACK: This is specific to Courtyard Koota
            # where dates are not in ISO format
            event[x] = event[x].replace("+5.5:00", "+05:30")
            time = year = None
            if "T" in event[x]:
                date, time = event[x].split("T")
                year, month, day = date.split("-")
            else:
                yy = event[x].split("-")
                if len(yy) == 3:
                    year, month, day = yy
            if year:
                month = month.zfill(2)
                day = day.zfill(2)
                event[x] = f"{year}-{month}-{day}"
                if time:
                    event[x] = f"{event[x]}T{time}"

    # fix format to ISO and timezone to IST
    for x in ["startDate", "endDate"]:
        if x in event:
            try:
                event[x] = datetime.fromisoformat(event[x]).astimezone(IST).isoformat()
            except Exception as e:
                # THIS IS BHAAGO INDIA SPECIFIC
                # replace all dots and commas
                startdate = event[x].replace(".", "").replace(",", "").lower()
                startdate = startdate.replace("sept", "sep")
                event[x] = (
                    list(datefinder.find_dates(startdate))[0]
                    .replace(tzinfo=IST)
                    .isoformat()
                )

    # set endDate = startDate + 2h if no endDate
    if "endDate" not in event:
        event["endDate"] = (
            datetime.fromisoformat(event["startDate"]) + timedelta(hours=2)
        ).isoformat()

    # force https here
    event["@context"] = "https://schema.org"

    # set a url if not already set
    if "url" not in event:
        event["url"] = url

    # HighApe events have a free entry offer with price 0
    # for all events, which is not shown on the website
    # so we drop that.
    try:
        if (
            url.startswith("https://highape.com")
            and event["offers"][-1]["price"] == "0"
            and event["offers"][-1]["name"] == "Entry"
        ):
            del event["offers"][-1]
    except KeyError:
        pass
    try:
        if isinstance(event["organizer"], list) and len(event["organizer"]) == 1:
            event["organizer"] = event["organizer"][0]
    except KeyError:
        pass


# This is a hacky selective deep-merge
# just for the keywords field
def apply_patch(event, patch={}):
    patch = patch.copy()
    if "keywords" in patch and "keywords" in event:

        if isinstance(event["keywords"], str):
            event["keywords"] = list(
                set([k.strip() for k in event["keywords"].split(",")])
            )
        patch["keywords"] = sorted(event["keywords"] + patch["keywords"])
        del event["keywords"]  # so it gets overridden for sure
    patch.update(event)
    return patch


def get_local_events(files, filt):
    for i in files:
        if filt and i != filt:
            continue

        patch = get_patch(i)
        start_ts = time.time()
        if os.path.exists(i):
            with open(i, "r") as f:
                data = json.load(f)
                for event in data:
                    if "@id" in event and event["@id"] in IGNORED_EVENT_UIDS:
                        continue
                    for x in ["startDate", "endDate"]:
                        if x in event:
                            try:
                                event[x] = (
                                    datetime.fromisoformat(event[x])
                                    .astimezone(IST)
                                    .isoformat()
                                )
                            except Exception as e:
                                print(f"Error parsing {x} for {event['url']}")

                    event = apply_patch(event, patch)
                    yield (event["url"], event)
            print(f"Processed {i} in {time.time() - start_ts:.2f}s")
        else:
            print(f"[ERROR] Missing {i}")


def get_events(s, filt):
    for i in URL_FILES:
        if filt and i != filt:
            continue
        with open(i, "r") as f:

            start_ts = time.time()
            patch = get_patch(i)
            urls = f.readlines()
            for url in urls:
                url = url.strip()
                if url:
                    keywords = None
                    r = s.get(url, headers=USER_AGENT_HEADERS)
                    base_url = get_base_url(r.text, r.url)
                    # extract the meta name="keywords" tag using bs4
                    soup = BeautifulSoup(r.text, "html.parser")
                    meta = soup.find("meta", attrs={"name": "keywords"})
                    if meta:
                        keywords = meta["content"]

                    if len(r.text) == 0:
                        print("No content for ", url)
                        break

                    def find_event(l):
                        for d in l:
                            if d.get("@type") in KNOWN_EVENT_TYPES:
                                return (url, d)

                    data = JsonLdExtractor().extract(r.text)
                    m = None
                    for x in data:
                        if x.get("@graph"):
                            m = m or find_event(x["@graph"])
                    m = m or find_event(data)

                    if m:
                        # together.buzz and skillboxes events don't have URL, duh
                        if m[1].get("LOCATION"):
                            m[1]["location"] = m[1].pop("LOCATION")
                        if keywords:
                            if "keywords" in m[1]:
                                # insider reports keywords as a dict (incorrectly) so we ignore and rewrite from meta tags
                                try:
                                    keywords = ",".join(
                                        set(
                                            m[1]["keywords"].split(",")
                                            + keywords.split(",")
                                        )
                                    )
                                except:
                                    pass
                            m[1]["keywords"] = keywords

                        # These are workarounds for broken schema published by Insider
                        try:
                            if "language" in m[1]["inLanguage"]:
                                m[1]["inLanguage"]["name"] = m[1]["inLanguage"][
                                    "language"
                                ]
                                m[1]["inLanguage"]["alternateName"] = LANGUAGE_MAP.get(
                                    m[1]["inLanguage"]["language"], "und"
                                )
                                del m[1]["inLanguage"]["language"]
                        except:
                            pass
                        try:
                            if m1["typicalAgeRange"]["@type"] == "Age-Range":
                                m[1]["typicalAgeRange"] = m[1]["typicalAgeRange"][
                                    "language"
                                ]
                        except:
                            pass
                        fix_online_schema(url, m[1])
                        event = apply_patch(m[1], patch)
                        yield (m[0], event)
                    else:
                        print(f"Could not find event in {url}")
            print(f"Processed {i} in {time.time() - start_ts:.2f}s")


def insert_event_json(conn, url, event_json):
    d = json.dumps(event_json)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO events (url, event_json) VALUES (?, ?)", (url, d))


def get_patch(input_file):
    basename = os.path.splitext(os.path.basename(input_file))[0]
    patch = os.path.join("patch", basename + ".json")
    if os.path.exists(patch):
        with open(patch, "r") as file:
            return json.load(file)
    return {}


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


if __name__ == "__main__":
    f = None
    if len(sys.argv) > 1:
        f = sys.argv[1]
    create_events_table()
    session = get_cached_session(allowable_codes=(200, 302))
    conn = sqlite3.connect("events.db")
    i = 0
    for url, d in get_events(session, f):
        insert_event_json(conn, url, d)
        i += 1
        if i % 10 == 0:
            conn.commit()

    for url, event in get_local_events(EVENT_JSON_FILES, f):
        insert_event_json(conn, url, event)
        i += 1
        if i % 10 == 0:
            conn.commit()
    conn.commit()
    conn.close()
