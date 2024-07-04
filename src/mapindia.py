from datetime import datetime, timedelta, timezone
from ics import Calendar, Event
from common.session import get_cached_session
from bs4 import BeautifulSoup
from common import USER_AGENT_HEADERS as HEADERS

"""
TODO: This script currently only works on Events, and not Exhibits or Installations
"""
session = get_cached_session(allowable_methods=["GET", "POST"])


def fetch_urls(month):
    url = "https://map-india.org/wp-admin/admin-ajax.php"

    payload = {
        "action": "load_homepage_posts",
        "filterWhen[]": month,
        "filterWhere[]": [
            "map-bengaluru",
            "offsite",
        ],  # TODO: Keep an eye out for offsite events and update location
        "setBeyond6Months": "false",
    }

    response = session.post(url, data=payload, headers=HEADERS)

    soup = BeautifulSoup(response.text, "html.parser")
    for link in soup.find_all("a", class_="ajax-posts-container__post__link"):
        yield link.get("href")


def generate_calendar():
    c = Calendar(creator="blr.today/map-india")
    months = [
        (datetime.now() + timedelta(days=30 * i)).strftime("%Y-%m") for i in range(2)
    ]
    for month in months:
        for url in fetch_urls(month):
            # Skip over exhibits since they don't have a calendar anyway
            if "/map-events/" not in url:
                continue

            # fetch the event
            response = session.get(url, headers=HEADERS)
            soup = BeautifulSoup(response.text, "html.parser")
            category = soup.select_one("article .sub-title").text
            response = session.get(url + "ical/", headers=HEADERS)
            if response.status_code == 200:
                for e in Calendar(response.text).events:
                    e.categories = [category, "MAP"]
                    c.events.add(e)
    return c


with open("out/mapindia.ics", "w") as f:
    c = generate_calendar()
    f.writelines(c.serialize_iter())
