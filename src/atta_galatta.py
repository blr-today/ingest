import datetime
import json
from requests_cache import CachedSession
import datefinder
from common.tz import IST
from bs4 import BeautifulSoup

session = CachedSession(
    "event-fetcher-cache",
    expire_after=datetime.timedelta(days=1),
    stale_if_error=True,
    use_cache_dir=True,
    cache_control=False,
)
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
    subtitle = divs[0].text.strip()
    performers = divs[1].text.strip()
    keywords = [x.strip() for x in divs[2].text.split("|")]

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
        "keywords": keywords + ["ATTAGALATTA", "BOOKSTORE"],
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
    data = [make_event(event) for event in fetch_events()]

    with open("out/atta_galatta.json", "w") as f:
        json.dump(data, f, indent=2)
