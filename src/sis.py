from bs4 import BeautifulSoup
import requests
from common.tz import IST
from html import escape
import json
import datetime
import re
import os
import datefinder

BASE_URL = "https://sistersinsweat.in"


def fetch_events_html(session):
    response = session.get(BASE_URL + "/events?city=4")
    return response.text


def fetch_sessions_html(session):
    response = session.get(BASE_URL + "/sessions?city=4&Sport=All")
    return response.text


def fix_date(date_str):
    return date_str.replace(" ", "T") + "+05:30"


def fetch_ajax_details(sku, _token):
    data = {"_token": _token, "sku": escape(sku, quote=False), "location_name": "4"}
    url = BASE_URL + "/getTimeSlotAjax"
    e = session.post(url, data=json.dumps(data), headers={"content-type": "application/json"}).json()
    try:
        e = e[0]
    except IndexError:
        print("[SIS] Failed to get schedule for " + sku)
        return None

    # The end_date is unreliable. The website uses the date from the start_date
    # and the time from the end_date as the actual endsAt

    endsAt = fix_date(e["start_date"].split(" ")[0] + " " + e["end_date"].split(" ")[1])

    return {
        "startDate": fix_date(e["start_date"]),
        "endDate": endsAt,
        "offers": [{"price": e["price"], "priceCurrency": "INR"}],
    }


def fetch_event_details(session, l):
    sport = l.split("/")[4]
    if sport == "packages":
        return None
    if sport == "yoga":
        event_type = "SocialEvent"
    else:
        event_type = "SportsEvent"
    response = session.get(l)
    html = response.text
    soup = BeautifulSoup(html, "html.parser")
    div = soup.select_one("#description")
    title = soup.select_one("h2").text
    # Not an event
    NOT_EVENT = ["subscription", "package"]
    for word in NOT_EVENT:
        if word in title.lower():
            return None
    event = {
        "name": title,
        "@type": event_type,
        "url": l,
        "@context": "https://schema.org",
        "keywords": ["SISTERSINSWEAT"],
        "audience": {"@type": "Audience", "AudienceType": "women"},
        "eventAttendanceMode": "OfflineEventAttendanceMode",
        "eventStatus": "EventScheduled",
        "inLanguage": "en",
        "organizer": {
            "@type": "Organization",
            "name": "Sisters In Sweat",
            "url": "https://sistersinsweat.in",
        },
    }
    # Since SISTERSINSWEAT events can be non-sport events as well
    # we add a secondary tag as well to help with filtering
    if sport in ["basketball", "football", "badminton", "running", "yoga", "pickleball"]:
        event["keywords"].append("SISTERSINSWEAT/SPORTS")
        event['sport'] = sport.title()
    else:
        event["keywords"].append("SISTERSINSWEAT/SESSION")

    if div:
        text = div.text.replace("\n \n", "\n")
        event["description"] = text.strip()
    img = soup.select_one("img.img-fluid")
    if img:
        event["image"] = img.get("src")
    v = soup.select_one("#venue")
    # Ignore virtual events
    if v:
        if "Virtual" in v.text:
            return None
        venue_text = v.text
        if "cubbon park" in venue_text.lower():
            venue_text = "Cubbon Park"
            venue_address = "Kasturba Road, Bangalore"
        else:
            venue_text = venue_text.replace("\r", "")
            venue_text = venue_text.replace(",", "\n")
            s = venue_text.split("\n")
            venue_text = s[0].strip()
            venue_address = ", ".join(s[1:])
        event["location"] = {
            "name": venue_text.strip(),
            "address": venue_address.strip(),
            "type": "Place",
        }
    sku = soup.select_one('input[name="sku"]').get("value")
    _token = soup.select_one('input[name="_token"]').get("value")
    event = event | fetch_ajax_details(sku, _token)
    if 'startDate' not in event:
        return None
    return event


def fetch_events_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select('a[href^="https://sistersinsweat.in/session_details/"]')
    return [link.get("href") for link in links]


if __name__ == "__main__":
    session = requests.Session()
    html = fetch_events_html(session)
    html2 = fetch_sessions_html(session)
    events = []
    for l in fetch_events_links(html) + fetch_events_links(html2):
        e = fetch_event_details(session, l)
        if e:
            events.append(e)
    with open("out/sis.json", "w") as f:
        json.dump(events, f, indent=2)
