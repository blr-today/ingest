import datetime
import time
from lxml import html
import json
from requests_cache import CachedSession
import datefinder
import extruct
import requests
import cloudscraper

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}
session = CachedSession(
    "event-fetcher-cache",
    expire_after=datetime.timedelta(days=1),
    stale_if_error=True,
    use_cache_dir=True,
    cache_control=False,
)
scraper = cloudscraper.create_scraper()

def apply_xpath(html_content, xpath_selector):
    tree = html.fromstring(html_content)
    return tree.xpath(xpath_selector)

def fetch_events():
    url = "https://linktr.ee/atta_galatta"
    r = session.get(url)
    xpath_selector = '//a[@rel="noopener" and @target="_blank" and not(@data-testid="SocialIcon")]'
    filtered_links = apply_xpath(r.text, xpath_selector)

=======
from common import linktree

def fetch_events():

    events = []
    l = linktree.Linktree("atta_galatta")
    for link in l.fetch_links():
        title = link['title']
        tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        dates = list(datefinder.find_dates(title, index=True))
        if dates:
            date = dates[-1][0]
            idx = dates[-1][1][0]
            startdate = dates[-1][0].replace(tzinfo=tz)
            events.append({
                "name": title[0:idx],
                "startDate": startdate.isoformat(),
                "endDate": (startdate+datetime.timedelta(hours=2)).isoformat(),
                'url': link.attrib['href']
                "thumbnail": link['thumbnail']
            })

    return events

def reformat_events():
    events = []
    for e in fetch_events():
        insert = False
        r = scraper.get(e['url'])
        data = extruct.extract(r.text, base_url=e['url'], syntaxes=["json-ld"])
        time.sleep(2)
        for x in data["json-ld"]:
            if x.get('@type') == "Event":
                events.append(x)
                insert = True
                break
        if not insert:
            events.append(e)

    return events

if __name__ == "__main__":
    with open("out/atta_galatta.json", "w") as f:
        json.dump(reformat_events(), f, indent=2)