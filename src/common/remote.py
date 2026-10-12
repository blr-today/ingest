from .jsonld import JsonLdExtractor
import glob
from .session import get_cached_session
from .schemaorg import TYPES as KNOWN_EVENT_TYPES
from . import USER_AGENT_HEADERS
import json
import sys
import os
import lxml.etree


def find_event(l):
    for d in l:
        if d.get("@type") in KNOWN_EVENT_TYPES:
            return d


def add_source(event, source):
    keywords = event.get("keywords", [])
    if isinstance(keywords, str):
        keywords = source.upper() + ", " + keywords
    elif isinstance(keywords, list):
        keywords = list(set([source.upper()] + keywords))
    event["keywords"] = keywords
    return event


def page_event(session, url):
    try:
        r = session.get(url, headers=USER_AGENT_HEADERS)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None
    if len(r.text) == 0:
        print("No content for ", url)
        return None

    try:
        data = JsonLdExtractor().extract(r.text)
    except json.decoder.JSONDecodeError:
        print(f"Error parsing JSON for {url}")
        return None
    except lxml.etree.ParserError:
        print(f"Error parsing HTML for {url}")
        return None

    event = None
    for x in data:
        if x.get("@graph"):
            event = event or find_event(x["@graph"])
    event = event or find_event(data)
    if not event:
        print(f"Could not find event in {url}")
    return event


def events_from_urls(urls):
    session = get_cached_session()
    events = (page_event(session, url) for url in map(str.strip, urls) if url)
    return [event for event in events if event]


def fetch_remote_events(file_filter=None):
    session = get_cached_session()
    URL_FILES = glob.glob("out/*.txt")
    for url_file in URL_FILES:
        if file_filter and url_file != file_filter:
            continue
        source = os.path.basename(url_file)[:-4]
        with open(url_file, "r") as f:
            for url in map(str.strip, f.readlines()):
                event = page_event(session, url) if url else None
                if event:
                    yield (url, add_source(event, source))
