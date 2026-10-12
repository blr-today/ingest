from src.common.session import get_cached_session
from datetime import date, datetime
import json


def urls():
    session = get_cached_session()
    found = []

    url = "https://api.together.buzz/v1/discovery/home?format=json&limit=10&pageCount=1"
    for event in session.get(url).json()["data"]:
        d = datetime.strptime(event["data"]["start_datetime"][0:10], "%Y-%m-%d").date()

        if d >= date.today():
            found.append(event["data"]["action"])
    return found
