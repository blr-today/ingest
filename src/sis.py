from bs4 import BeautifulSoup
from common.session import get_cached_session
import json
import datetime
import re
import os
from urllib.parse import urlencode


def fetch_events_html():
    session = get_cached_session()
    response = session.get("https://sistersinsweat.in/events?city=4")
    return response.text


def read_events_html():
    with open("fixtures/sisters-in-sweat.html", "r") as f:
        return f.read()


def fetch_event_details(l):
    session = get_cached_session()
    response = session.get(l)
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    div = soup.select_one("#description").text.replace("\n\n", "\n")
    print(div)


def fetch_events_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select('a[href^="https://sistersinsweat.in/session_details/"]')
    return [link.get("href") for link in links]


html = read_events_html()
for l in fetch_events_links(html):
    fetch_event_details(l)
