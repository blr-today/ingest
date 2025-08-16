from common.jsonld import JsonLdExtractor
import glob
from common.session import get_cached_session
from w3lib.html import get_base_url
from bs4 import BeautifulSoup
from common.schemaorg import TYPES as KNOWN_EVENT_TYPES
from common import USER_AGENT_HEADERS
import json
import sys
import os

def find_event(l):
    for d in l:
        if d.get("@type") in KNOWN_EVENT_TYPES:
            return d

def fetch_remote_events(file_filter = None):
    session = get_cached_session()
    URL_FILES = glob.glob("out/*.txt")
    for url_file in URL_FILES:
        if file_filter and url_file != file_filter:
            continue
        with open(url_file, "r") as f:
            urls = f.readlines()
            for url in urls:
                url = url.strip()
                if not url:
                    break
                keywords = None
                r = session.get(url, headers=USER_AGENT_HEADERS)
                base_url = get_base_url(r.text, r.url)
                # extract the meta name="keywords" tag using bs4
                soup = BeautifulSoup(r.text, "html.parser")
                meta = soup.find("meta", attrs={"name": "keywords"})
                if meta:
                    keywords = meta["content"]

                if len(r.text) == 0:
                    print("No content for ", url)
                    break
                
                try:
                    data = JsonLdExtractor().extract(r.text)
                except json.decoder.JSONDecodeError:
                    print(f"Error parsing JSON for {url}")
                    pass

                event = None
                for x in data:
                    if x.get("@graph"):
                        event = event or find_event(x["@graph"])
                event = event or find_event(data)
                if event:
                    yield (url, event)
                else:
                    print(f"Could not find event in {url}")
