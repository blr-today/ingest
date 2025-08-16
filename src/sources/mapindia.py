from datetime import datetime, timedelta, timezone
from ics import Calendar, Event
from common.session import get_cached_session
from bs4 import BeautifulSoup
from common import USER_AGENT_HEADERS as HEADERS

"""
TODO: This script currently only works on Events, and not Exhibits or Installations
"""
session = get_cached_session(allowable_methods=["GET", "POST", "HEAD"])


def fetch_urls(exclude_ids = []):
    data = {"action": "load_filtered_events"}
    if len(exclude_ids) > 0:
        data["excludeIds[]"] = exclude_ids
    response = session.post(
        "https://map-india.org/wp/wp-admin/admin-ajax.php",
        headers=HEADERS,
        data=data,
    ).json()
    for post_id in response['current_posts']:
        yield f"https://map-india.org/?p={post_id}"
    if 'loadMore' in response and response['loadMore'] == True:
        yield from fetch_urls([str(x) for x in response['current_posts']] + exclude_ids)

def generate_calendar():
    c = Calendar(creator="blr.today/map-india")
    for url in fetch_urls():
        # Since we are using post IDs, we have to check for redirects.
        url = session.head(url, headers=HEADERS).headers["Location"]

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
                e.categories = [category, "MAP", "CBD"]
                c.events.add(e)
    return c


with open("out/mapindia.ics", "w") as f:
    c = generate_calendar()
    f.writelines(c.serialize_iter())
    print(f"[MAP] {len(c.events)} events")

