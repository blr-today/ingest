import datetime
import json
import cleanurl
from common.tz import IST
import dateutil.parser
import re
from lxml import etree
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
        return (str(ceil(float(variant["price"]))), j["product"]["product_type"])


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
def make_event(title, starttime, endtime, description, url, product_urls):
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
    endtime = (endtime or starttime + datetime.timedelta(hours=2)).replace(tzinfo=IST)
    parts = [p.strip() for p in title.split("|")]
    name = " | ".join(p for p in parts if not (re.search(r"\d", p) and len(p) < 25))

    e = {
        "@type": guess_event_type(title),
        "name": name,
        "startDate": starttime.isoformat(),
        "endDate": endtime.isoformat(),
        "description": description,
        "url": url,
        "offers": [],
    }

    for product_url in product_urls:
        handle = get_product_handle(product_url)
        if not handle:
            print(f"[CHAMPACA] Could not get handle for {product_url}")
            continue
        price, type = get_product_details(handle)
        # TODO: If Needed
        # Champaca does not mark its events in a separate category always
        # So we can check the product weight, which should be zero as well
        if "ticket" in type.lower() or "event" in type.lower():
            e["offers"].append(
                {
                    "@type": "Offer",
                    "url": product_url,
                    "price": price,
                    "priceCurrency": "INR",
                }
            )
            if price == "0":
                e["isAccessibleForFree"] = True

    if performer:
        e["performer"] = {"@type": "Person", "name": performer}

    return e


TIME_RE = r"\d{1,2}(?::\d{2})?\s*[ap]\.?m"


def parse_schedule(text, published):
    text = re.sub(r"\s+", " ", text.replace("\xa0", " "))
    date_match = re.search(r"Date:\s*(.+?)(?=Time:|Venue:|Price:|$)", text)
    if not date_match:
        return None, None
    # Multi-day ranges like "26th and 27th September" start on the first day
    date_str = re.sub(
        r"(\d{1,2})(?:st|nd|rd|th)?\s*(?:and|&|-|to)\s*\d{1,2}(?:st|nd|rd|th)?",
        r"\1",
        date_match.group(1),
    )
    date_str = re.sub(r"[()&]", " ", date_str)
    time_match = re.search(r"Time:\s*(.+?)(?=Venue:|Price:|Date:|$)", text)
    time_str = re.sub(r"\(.*?\)", "", time_match.group(1)) if time_match else ""
    times = re.findall(TIME_RE, time_str, re.IGNORECASE)
    default = datetime.datetime(published.year, published.month, published.day)
    try:
        start = dateutil.parser.parse(date_str, fuzzy=True, default=default)
        if start < default:
            start = start.replace(year=start.year + 1)
        if times:
            start = dateutil.parser.parse(times[0], default=start)
        end = dateutil.parser.parse(times[1], default=start) if len(times) > 1 else None
    except ValueError, OverflowError:
        return None, None
    return start, end


def fetch_events():
    url = "https://champaca.in/blogs/events.atom"
    res = make_request(url)

    try:
        tree = etree.fromstring(res.text.encode("utf-8"))
    except etree.XMLSyntaxError:
        return []

    ns = {"xmlns": "http://www.w3.org/2005/Atom"}
    events = []
    now = datetime.datetime.now()

    for entry in tree.xpath("//xmlns:entry", namespaces=ns):
        title = entry.find(".//xmlns:title", namespaces=ns).text
        if "online" in title.lower():
            continue
        html_content = entry.find(".//xmlns:content", namespaces=ns).text
        if not html_content:
            continue
        published = dateutil.parser.parse(
            entry.find(".//xmlns:published", namespaces=ns).text
        )
        doc = etree.HTML(html_content)
        description_text = " ".join(doc.xpath("//div//text() | //p//text()"))
        url = entry.find(".//xmlns:link", namespaces=ns).attrib["href"]
        links = doc.xpath(
            '//a[starts-with(@href, "https://champaca.in/products/")]/@href'
        )

        start, end = parse_schedule(" ".join(doc.xpath("//text()")), published)
        if not start:
            print(f"[CHAMPACA] Could not find date for {title}")
            continue
        if 0 <= (start - now).days <= 30:
            events.append(make_event(title, start, end, description_text, url, links))

    return events


if __name__ == "__main__":
    events = fetch_events()
    with open("out/champaca.json", "w") as f:
        json.dump(events, f, indent=2)
    print(f"[CHAMPACA] {len(events)} events")
