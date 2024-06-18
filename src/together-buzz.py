import extruct
from requests_cache import CachedSession
from datetime import timedelta,date,datetime
import json

def scrape_together():
    session = CachedSession(
        "event-fetcher-cache",
        expire_after=timedelta(days=1),
        stale_if_error=True,
        use_cache_dir=True,
        cache_control=False,
    )

    url = "https://api.together.buzz/v1/discovery/home?format=json&limit=10&pageCount=1"
    for event in session.get(url).json()['data']:
        d = datetime.strptime(event['data']['start_datetime'][0:10], '%Y-%m-%d').date()

        if d>= date.today():
            print(event['data']['action'])
    
scrape_together()