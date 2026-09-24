import datetime
import json
from common.session import get_cached_session
import datefinder
from common.tz import IST
from bs4 import BeautifulSoup

session = get_cached_session()
# TODO: Some events have more than one event, we don't handle that case
"""
Fetches events in the future
and attaches a datetime object to each event
"""


def fetch_events():
    events = []
    for event in session.get("https://attagalatta.com/events.php").json()["value"]:
        dates = list(datefinder.find_dates(event["eventday"]))
        if len(dates) > 0 and dates[0].date() > datetime.datetime.today().date():
            event["date"] = dates[0].replace(tzinfo=IST)
            yield event


def make_event(event):
    response = session.get(event["link"])
    soup = BeautifulSoup(response.text, "html.parser")
    maybeClosingTime = soup.select_one("#after-title").text.split("-")[1].strip()
    description = soup.select_one("#product-content").text.strip()

    divs = soup.select(".product-attribute")
    # some events omit trailing attribute divs (e.g. no keywords)
    subtitle = divs[0].text.strip() if len(divs) > 0 else ""
    performers = divs[1].text.strip() if len(divs) > 1 else ""
    keywords = [x.strip() for x in divs[2].text.split("|")] if len(divs) > 2 else []

    startTime = list(
        datefinder.find_dates(event["eventstarttime"], base_date=event["date"])
    )
    endTime = list(datefinder.find_dates(maybeClosingTime, base_date=event["date"]))

    e = {
        "name": event["title"] + " - " + subtitle,
        "description": description if len(description) > 0 else event["description"],
        "url": event["link"],
        "image": event["image"],
        "performer": performers,
        "keywords": keywords,
    }

    if (
        "Book" in e["name"]
        or "Author" in e["name"]
        or "Literary Discussion" in e["keywords"]
        or "Poetry" in e["keywords"]
    ):
        e["@type"] = "LiteraryEvent"

    elif subtitle == "Theatre Performance":
        e["@type"] = "TheatreEvent"
    elif "Music Performance" in e["name"]:
        e["@type"] = "MusicEvent"

    elif "Children" in e["name"]:
        e["@type"] = "ChildrensEvent"

    elif "Screening" in e["keywords"]:
        e["@type"] = "ScreeningEvent"

    elif "Discussion" in e["keywords"] or "Social" in e["keywords"]:
        e["@type"] = "SocialEvent"
    elif "Workshop" in e["keywords"]:
        e["@type"] = "EducationEvent"
    else:
        e["@type"] = "LiteraryEvent"

    if len(startTime) > 0:
        e["startDate"] = startTime[0].replace(tzinfo=IST).isoformat()
    if len(endTime) > 0:
        e["endDate"] = endTime[0].replace(tzinfo=IST).isoformat()
    return e


if __name__ == "__main__":
    data = []
    for event in fetch_events():
        try:
            data.append(make_event(event))
        except Exception as e:
            print(f"skipping event {event.get('link')}: {e}")

    with open("out/atta_galatta.json", "w") as f:
        json.dump(data, f, indent=2)
