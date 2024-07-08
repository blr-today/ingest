from extruct.jsonld import JsonLdExtractor
from common.session import get_cached_session
from bs4 import BeautifulSoup
from datetime import datetime
import json


def scrape_cm(location):
    session = get_cached_session()

    url = f"https://creativemornings.com/cities/{location}"
    soup = BeautifulSoup(session.get(url).content, "html.parser")
    event_links = set()
    for link in soup.select("a[href^='/talks/']"):
        if (
            link["href"] != "/talks/upcoming"
            and "play=" not in link["href"]
            and link["href"][-2] != "/"
        ):
            event_links.add(link["href"])

    for link in event_links:
        l = f"https://creativemornings.com{link}"
        r = session.get(l)
        data = JsonLdExtractor().extract(r.text)

        try:
            d = datetime.strptime(
                data[0]["startDate"].split("T")[0], "%Y-%m-%d"
            )
            # check if date is in the future
            if d > datetime.now():
                print(l)
        except:
            pass


scrape_cm("BLR")
