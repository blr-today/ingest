import json
from common import firebase
from common.session import get_cached_session
from bs4 import BeautifulSoup
from datetime import datetime
from common.tz import IST

URL = "https://firestore.googleapis.com/v1/projects/tonight-is/databases/(default)/documents/parties?pageSize=1000"


def fetch_parties():
    session = get_cached_session()
    return session.get(URL).json()


def convert_to_event_json(event):
    lat, lng = [x.strip() for x in event["venues"][0]["location"].split(",")]
    startdate = datetime.fromisoformat(event["startDate"]).astimezone(IST)
    enddate = datetime.fromisoformat(event["endDate"]).astimezone(IST)
    return {
        "@type": "MusicEvent",
        "name": event["name"],
        "about": event["description"],
        "sameAs": event["webUrl"] if "undefined" not in event["webUrl"] else None,
        "url": event['ticketUrl'],
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
            "geo": {"@type": "GeoCoordinates", "latitude": lat, "longitude": lng},
        },
        "organizer": {
            "@type": "Organization",
            "name": event["organisers"][0]["name"],
        },
        "offers": {
            "@type": "Offer",
            "url": event["ticketUrl"],
        },
    }


with open("fixtures/tonight-is-parties.json", "r") as f:
    # drop all events with startDate in the past
    data = firebase.Firebase.parse_firebase_struct(fetch_parties()["documents"])
    data = [
        convert_to_event_json(e)
        for e in data
        if datetime.fromisoformat(e["startDate"]).date() > datetime.now().date()
    ]

    with open("out/tonight.json", "w") as file:
        json.dump(data, file, indent=2)
