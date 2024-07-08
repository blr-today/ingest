from common.session import get_cached_session
from datetime import date, datetime
import json


def scrape_together():
    session = get_cached_session()

    url = "https://api.together.buzz/v1/discovery/home?format=json&limit=10&pageCount=1"
    for event in session.get(url).json()["data"]:
        d = datetime.strptime(event["data"]["start_datetime"][0:10], "%Y-%m-%d").date()

        if d >= date.today():
            print(event["data"]["action"])


scrape_together()
