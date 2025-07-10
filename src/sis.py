from bs4 import BeautifulSoup
import requests
from common.tz import IST
from html import escape
import json
import datetime
import re
import os
import datefinder

BASE_URL = "https://sistersinsweat.com"

def fetch_sessions_html(session):
    body = """{
      "City": "BENGALURU"
    }
    """
    response = session.post(BASE_URL + "/filter-events", data=body, headers={
        "content-type": "application/json"
    })
    return response.text

def make_event_details(soup):
    l = soup.select_one(".box-button a").get("href")
    if "package-detail" in l:
        return None
    if "Yoga" in l:
        event_type = "SocialEvent"
    elif "Pizza" in l or "cooking" in l:
        event_type = "FoodEvent"
    else:
        event_type = "SportsEvent"
    description = f"See more details at {BASE_URL + l}"
    # Remove the price from the description
    title = soup.select_one(".title").text.strip()
    # Not an event
    NOT_EVENT = ["subscription", "package"]
    for word in NOT_EVENT:
        if word in title.lower():
            return None
    event = {
        "name": title,
        "@type": event_type,
        "url": BASE_URL + l,
        "@context": "https://schema.org",
        "keywords": ["SISTERSINSWEAT"],
        "audience": {"@type": "Audience", "AudienceType": "women"},
        "eventAttendanceMode": "OfflineEventAttendanceMode",
        "eventStatus": "EventScheduled",
        "inLanguage": "en",
        "organizer": {
            "@type": "Organization",
            "name": "Sisters In Sweat",
            "url": "https://sistersinsweat.com",
        },
    }
    # Since SISTERSINSWEAT events can be non-sport events as well
    # we add a secondary tag as well to help with filtering
    if event_type == "SportsEvent":
        event["keywords"].append("SISTERSINSWEAT/SPORTS")
        event['sport'] = l.split("-")[3]
    else:
        event["keywords"].append("SISTERSINSWEAT/SESSION")

    event["description"] = description.replace("\n \n", "\n").strip()
    
    img = soup.select_one(".box-image img")
    if img:
        event["image"] = img.get("src")
    v = soup.select_one(".box-city h3")
    # Ignore virtual events
    if v:
        if "Virtual" in v.text:
            return None
        venue_text = v.text
        if "cubbon park" in venue_text.lower():
            venue_text = "Cubbon Park"
            venue_address = "Kasturba Road, Bangalore"
        else:
            venue_address = v.find_next("p").text
            # Drop all text after ", Bengaluru"
            if ", Bengaluru" in venue_address:
                venue_address = venue_address.split(", Bengaluru")[0]
        event["location"] = {
            "name": venue_text.strip(),
            "address": venue_address.strip(),
            "type": "Place",
        }
    date = soup.select_one(".box-date")
    if date:
        date_text = date.select_one(".box-date .date-text3").text
        # Remove the time from the date text
        date_text = re.sub(r"\d{1,2}:\d{2} [AP]M", "", date_text).strip()
        # Find the date in the text
        matches = list(datefinder.find_dates(date_text))
        if matches:
            event["startDate"] = matches[0].replace(tzinfo=IST).isoformat()
            event["endDate"] = (matches[0] + datetime.timedelta(hours=1)).replace(tzinfo=IST).isoformat()
    else:
        print("No date found " + l)
        return None
    return event


def fetch_event_boxes(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.select('.list-view-box')

if __name__ == "__main__":
    session = requests.Session()
    html = fetch_sessions_html(session)
    events = []
    for box_soup in fetch_event_boxes(html):
        e = make_event_details(box_soup)
        if e:
            events.append(e)
    with open("out/sis.json", "w") as f:
        json.dump(events, f, indent=2)
