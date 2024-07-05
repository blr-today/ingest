import json
import requests
import urllib.parse
from common.session import get_cached_session
import cleanurl
from datetime import datetime, timedelta

KNOWN_SHORTENERS = ["bit.ly"]


def expand_link(session, url):
    response = session.head(url, allow_redirects=False, timeout=5)
    if "location" in response.headers:
        return response.headers["location"]
    return url


def make_event(event):
    # We assume 2 hours
    endDate = datetime.fromisoformat(event["event_date"]) + timedelta(hours=2)
    return {
        "id": f"buzz.venn:{event['id']}",
        "name": event["title"],
        "image": event["large_image"],
        "location": {
            "name": event["venue"]["name"],
            "address": event["venue"]["name"] + " Bangalore",
        },
        "url": f"https://app.venn.buzz/social_experience/{event['id']}",
        "sameAs": event["url"],
        "startDate": event["event_date"],
        "endDate": endDate.isoformat(),
        "description": event["short_description"],
    }


def fetch_venn():
    session = get_cached_session(allowable_codes=(200, 302), days=7)
    events = []
    event_ids = set()
    url = f"https://api.venn.buzz/user/social_experiences.json?filter=all"

    api_response = requests.get(url).json()
    for event in api_response["data"]["events"]:
        while True:
            # get hostname from the URL
            hostname = urllib.parse.urlparse(event["shortened_link"]).hostname
            # if the hostname is a known shortener, expand the link
            if hostname in KNOWN_SHORTENERS:
                event["shortened_link"] = expand_link(session, event["shortened_link"])
            else:
                break
        event["url"] = cleanurl.cleanurl(
            event["shortened_link"], respect_semantics=True
        ).url

        for k in ["curation", "shortened_link", "test_event", "experience_id"]:
            if k in event:
                del event[k]
        if event["id"] not in event_ids:
            event_ids.add(event["id"])
            events.append(make_event(event))

    return sorted(events, key=lambda x: x["id"])


# Write to venn.json
if __name__ == "__main__":
    with open("out/venn.json", "w") as f:
        json.dump(fetch_venn(), f, indent=2)
