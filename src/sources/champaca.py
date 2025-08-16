import datetime
import json
import cleanurl
from common.tz import IST
import dateutil.parser
import re
from lxml import etree
import datefinder
import urllib.parse
from math import ceil
from bs4 import BeautifulSoup
from common.session import get_cached_session


def make_request(url):
    session = get_cached_session()
    return session.get(url)
    return response


def get_product_details(handle):
    url = f"https://champaca.in/products/{handle}.json"
    response = make_request(url)
    j = response.json()
    for variant in j["product"]["variants"]:
        return (str(ceil(float(variant["price"]))), j['product']['product_type'])

"""
Shopify URLs published in blogs 
do not always work for the API
because they have the wrong "handle"
This makes a correct product handle using the canonical ref
"""
def get_product_handle(url):
    response = make_request(url)
    soup = BeautifulSoup(response.text, "html.parser")
    canonical_link = soup.find("link", rel="canonical")
    if canonical_link:
        canonical_url = canonical_link["href"]
        parsed_url = urllib.parse.urlparse(canonical_url)
        return parsed_url.path.split("/")[-1]
    return None

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
        "name": title.split("|")[0].strip(),
        "startDate": starttime.isoformat(),
        "endDate": (starttime + datetime.timedelta(hours=2)).isoformat(),
        "description": description,
        "url": url,
        "offers": []
        
    }

    for product_url in product_urls:
        handle = get_product_handle(product_url)
        if not handle:
            print(f"[CHAMPACA] Could not get handle for {product_url}")
            continue
        price,type = get_product_details(handle)
        # TODO: If Needed
        # Champaca does not mark its events in a separate category always
        # So we can check the product weight, which should be zero as well
        if 'ticket' in type.lower() or 'event' in type.lower():
            e['offers'].append({
                "@type": "Offer",
                "url": product_url,
                "price": price,
                "priceCurrency": "INR"
            })
            if price == "0":
                e["isAccessibleForFree"] = True

    if performer:
        e["performer"] = {"@type": "Person", "name": performer}

    return e


def fetch_events():
    url = "https://champaca.in/blogs/events.atom"
    res = make_request(url)

    try:
        tree = etree.fromstring(res.text.encode('utf-8'))
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
        if "online" in title.lower():
            continue
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
                if days_difference <= 30 and days_difference >= 0:

                    events.append(
                        make_event(title, future_date, description_text, url, links)
                    )

    return events


if __name__ == "__main__":
    events = fetch_events()
    with open("out/champaca.json", "w") as f:
        json.dump(events, f, indent=2)
    print(f"[CHAMPACA] {len(events)} events")
