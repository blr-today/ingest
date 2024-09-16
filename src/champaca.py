import datetime
import json
from common.tz import IST
import dateutil.parser
import re
from lxml import etree
import datefinder
import urllib.parse
from math import ceil
from common.session import get_cached_session


def make_request(url):
    session = get_cached_session()
    response = session.get(url)
    return response.content


def get_price(product_url):
    session = get_cached_session()
    parsed_url = urllib.parse.urlparse(product_url)
    path = parsed_url.path
    response = session.get("https://champaca.in" + path + ".json")
    j = response.json()
    for variant in j["product"]["variants"]:
        return str(ceil(float(variant["price"])))


def guess_event_type(title):
    if "Workshop" in title:
        return "EducationEvent"
    if "Book" in title:
        return "LiteraryEvent"
    if "Children" in title:
        return "ChildrensEvent"
    return "Event"


# Generate as per the schema.org/Event specification
def make_event(title, starttime, description, url, product_urls):
    performer_regexes = [
        r"/by (?P<name>(\w|\s)+)\s(\||:)/",
        r"/with (?P<name>(\w|\s)+)\s(\||:)/",
    ]
    performer = None
    for regex in performer_regexes:
        match = re.search(regex, title)
        if match:
            performer = match.group("name")
            break
    starttime = starttime.replace(tzinfo=IST)

    e = {
        "@type": guess_event_type(title),
        "name": title,
        "startDate": starttime.isoformat(),
        "endDate": (starttime + datetime.timedelta(hours=2)).isoformat(),
        "description": description,
        "url": url,
        "offers": [
            {
                "@type": "Offer",
                "url": url,
                "price": get_price(url),
                "priceCurrency": "INR",
            }
            for url in product_urls
        ],
    }

    for offer in e["offers"]:
        if offer["price"] == "0":
            e["isAccessibleForFree"] = True

    if performer:
        e["performer"] = {"@type": "Person", "name": performer}

    return e


def fetch_events():
    url = "https://champaca.in/blogs/events.atom"
    content = make_request(url)

    try:
        tree = etree.fromstring(content)
    except etree.XMLSyntaxError:
        return []

    events = []

    # Iterate over each entry in the feed
    for entry in tree.xpath(
        "//xmlns:entry", namespaces={"xmlns": "http://www.w3.org/2005/Atom"}
    )[0:5]:
        title = entry.find(
            ".//xmlns:title", namespaces={"xmlns": "http://www.w3.org/2005/Atom"}
        ).text
        html_content = entry.find(
            ".//xmlns:content", namespaces={"xmlns": "http://www.w3.org/2005/Atom"}
        ).text
        # get all text from div or P elements
        description_text = " ".join(
            [p for p in etree.HTML(html_content).xpath("//div//text() | //p//text()")]
        )
        url = entry.find(
            ".//xmlns:link", namespaces={"xmlns": "http://www.w3.org/2005/Atom"}
        ).attrib["href"]

        doc = etree.HTML(html_content)
        links = doc.xpath(
            '//a[starts-with(@href, "https://champaca.in/products/")]/@href'
        )
        # Find future dates in the title
        future_dates = list(datefinder.find_dates(title, index=True, source=True))
        if future_dates:
            # Get the first future date found
            future_date = next(
                (
                    date
                    for date, idx, src in future_dates
                    if date > datetime.datetime.now()
                ),
                None,
            )
            if future_date:
                # Calculate the difference in days between now and the future date
                days_difference = (future_date - datetime.datetime.now()).days
                if days_difference <= 30 and days_difference >= 1:

                    events.append(
                        make_event(title, future_date, description_text, url, links)
                    )

    return events


if __name__ == "__main__":
    events = fetch_events()
    with open("out/champaca.json", "w") as f:
        json.dump(events, f, indent=2)
    print(f"[CHAMPACA] {len(events)} events")
