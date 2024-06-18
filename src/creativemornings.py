import extruct
from requests_cache import CachedSession
from bs4 import BeautifulSoup
from datetime import timedelta,datetime
import json

def scrape_cm(location):
    session = CachedSession(
        "event-fetcher-cache",
        expire_after=timedelta(days=1),
        stale_if_error=True,
        use_cache_dir=True,
        cache_control=False,
    )

    url = f"https://creativemornings.com/cities/{location}"
    soup = BeautifulSoup(session.get(url).content, "html.parser")
    event_links = set()
    for link in soup.select("a[href^='/talks/']"):
        if link['href'] != "/talks/upcoming" and 'play=' not in link['href'] and link['href'][-2] != '/':
            event_links.add(link['href'])

    for link in event_links:
        l = f"https://creativemornings.com{link}"
        r = session.get(l)
        data = extruct.extract(
            r.text, base_url="https://creativemornings.com/", syntaxes=["json-ld"]
        )

        try:
            d  = datetime.strptime(data['json-ld'][0]['startDate'].split('T')[0], '%Y-%m-%d')
            # check if date is in the future
            if d > datetime.now():
                print(l)
        except:
            pass

scrape_cm('BLR')