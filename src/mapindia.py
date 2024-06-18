from datetime import datetime, timedelta, timezone
from ics import Calendar,Event
from requests_cache import CachedSession
from bs4 import BeautifulSoup

# This currently only works on Events, and not Exhibits or Installations
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
session = CachedSession(
    "event-fetcher-cache",
    expire_after=timedelta(days=1),
    stale_if_error=True,
    use_cache_dir=True,
    cache_control=False,
)

def fetch_urls(month):
    url = "https://map-india.org/wp-admin/admin-ajax.php"

    payload = {
      "action": "load_homepage_posts",
      "filterWhen[]": "2024-06",
      "filterWhere[]": ["map-bengaluru", "offsite"],
      "setBeyond6Months": "false"
    }
    headers = {
        "content-type": "application/x-www-form-urlencoded", 
        'user-agent': USER_AGENT
    }

    response = session.post(url, data=payload, headers=headers)

    soup = BeautifulSoup(response.text, "html.parser")
    # find ajax-posts-container__post__link
    for link in soup.find_all("a", class_="ajax-posts-container__post__link"):
        yield link.get("href") + 'ical/'

def generate_calendar():
    c = Calendar(creator="blr.today/map-india")
    months = [(datetime.now() + timedelta(days=30 * i)).strftime("%Y-%m") for i in range(2)]
    for month in months:
        for url in fetch_urls(month):
            # Skip over exhibits since they don't have a calendar anyway
            if "/map-events/" not in url:
                continue
            response = session.get(url, headers={"User-Agent": USER_AGENT})
            if response.status_code == 200:
                for e in Calendar(response.text).events:
                    c.events.add(e)
    return c

with open('out/mapindia.ics', 'w') as f:
    c = generate_calendar()
    f.writelines(c.serialize_iter())