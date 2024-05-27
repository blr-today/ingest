import http.client
from bs4 import BeautifulSoup
import json
import datetime
import re
import os
from urllib.parse import urlencode


def fetch_events_html():
    connection = http.client.HTTPSConnection("sistersinsweat.in")
    connection.request("GET", "/events?city=4")
    response = connection.getresponse()
    return response.read().decode('utf-8')

def read_events_html():
    with open('fixtures/sisters-in-sweat.html', 'r') as f:
        return f.read()

def fetch_event_details(l):
    # html = request.get(l).contents
    with open('fixtures/sisters-in-sweat-event.html', 'r') as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    div = soup.select_one('#description').text.replace("\n\n", "\n")
    print(div)

def fetch_events_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select('a[href^="https://sistersinsweat.in/session_details/"]')
    return [link.get("href") for link in links]

html = read_events_html()
for l in fetch_events_links(html):
    fetch_event_details(l)