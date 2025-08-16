import json
from common import firebase
from common.session import get_cached_session
from bs4 import BeautifulSoup
from datetime import datetime
from common.tz import IST

URL = "https://firestore.googleapis.com/v1/projects/tonight-is/databases/(default)/documents/parties?pageSize=1000"

FALLBACK_URL_MAP = {
    "TPMygSSqmlO6qnhm7gaG": "https://www.district.in/events/echoes-of-earth-music-festival-2025-buy-tickets",
    "K4K7tvJ6uyvuMg7vnN3W": "https://www.district.in/events/darkroom-ft-deborah-de-luca-sep27-2025-buy-tickets"
}

def fetch_parties(cursor = None, url=URL):
    session = get_cached_session()
    if cursor:
        url = f"{URL}&pageToken={cursor}"

    response = session.get(url).json()
    yield from response['documents']
    if "nextPageToken" in response:
        yield from fetch_parties(cursor=response["nextPageToken"])

def get_url(event):
    if 'id' in event:
        return f"https://www.tonight.is/party/{event['id']}"
    return get_ticket_url(event)

def get_ticket_url(event):
    return FALLBACK_URL_MAP.get(event.get('id', None), event['ticketUrl'])

def convert_to_event_json(event):
    lat, lng = [x.strip() for x in event["venues"][0]["location"].split(",")]
    startdate = datetime.fromisoformat(event["startDate"]).astimezone(IST)
    enddate = datetime.fromisoformat(event["endDate"]).astimezone(IST)

    e = {
        "@type": "MusicEvent",
        "name": event["name"],
        "about": event["description"],
        "url": get_url(event),
        "startDate": startdate.isoformat(),
        "endDate": enddate.isoformat(),
        "image": (
            event["bannerImages"][0]["downloadURL"]
            if "bannerImages" in event and len(event["bannerImages"]) > 0
            else None
        ),
        "performer": {
            "@type": "MusicGroup",
            "name": event["artists"][0]["name"],
            # check if imageUrl or None
            # "image": event['artists'][0]['imageUrl'] if 'imageUrl' in event['artists'][0] else None
        },
        "location": {
            "@type": "Place",
            "name": event["venues"][0]["name"],
            "address": {
                "@type": "PostalAddress",
                "streetAddress": event["venues"][0]["description"],
                "addressLocality": event["city"],
                "addressRegion": "Karnataka",
                "addressCountry": "IN",
            },
        },
        "organizer": {
            "@type": "Organization",
            "name": event["organisers"][0]["name"],
        },
        "offers": {
            "@type": "Offer",
            "url": get_ticket_url(event),
        },
    }
    e["sameAs"] = get_ticket_url(event)
    if lat != "0" and lng !="0":
        e['location']["geo"]: {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng}

    return e


with open("fixtures/tonight-is-parties.json", "r") as f:
    
    data = list(fetch_parties())
    data = firebase.Firebase.parse_firebase_struct(data)
    data = [
        convert_to_event_json(e)
        for e in data
        if 'startDate' in e and datetime.fromisoformat(e["startDate"]).date() > datetime.now().date()
    ]

    with open("out/tonight.json", "w") as file:
        json.dump(data, file, indent=2)
