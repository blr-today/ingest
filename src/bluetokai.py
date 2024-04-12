import http.client
import json
import re
from bs4 import BeautifulSoup
import datefinder
from datetime import datetime, timezone, timedelta
import os
from math import ceil

LOCATIONS = [
    (
        "https://cafe.bluetokaicoffee.com/sarvagna-nagar-bengaluru-34817/home",
        "Blue Tokai Coffee Roasters HRBR Layout",
        r'\bhrbr\b',
    ),
    (
        "https://cafe.bluetokaicoffee.com/jayanagar-bengaluru-34903/home",
        "Blue Tokai Coffee Roasters Jayanagar",
        r'\bjayanagar\b',
    ),
    (
        "https://cafe.bluetokaicoffee.com/armane-nagar-bengaluru-34815/home",
        "Blue Tokai Coffee Roasters Sadashiva Nagar",
        r'\bsadashiva\b',
    ),
    (
        "https://cafe.bluetokaicoffee.com/mahadevapura-bengaluru-33593/home",
        "Blue Tokai Coffee Roasters Whitefield",
        r'\bwhitefield\b',
    ),
    # This is not a cafe but their Roastery itself
    (  
        "https://maps.app.goo.gl/fssZvwfXuxhaC7G77",
        "Blue Tokai Roastery, NGEF Layout",
        r'\bngef\b',
    ),
    (
        "https://cafe.bluetokaicoffee.com/shivaji-nagar-bengaluru-33592/home",
        "Blue Tokai Coffee Roasters Infantry Road",
        r'\binfantry\b',
    ),
    (
        "https://cafe.bluetokaicoffee.com/indiranagar-bengaluru-34282/home",
        "Blue Tokai Coffee Roasters Indiranagar, Domlur",
        r'\bdomlur\b',
    ),
    (
        "https://cafe.bluetokaicoffee.com/indiranagar-bengaluru-33590/home",
        "Blue Tokai Coffee Roasters Indiranagar",
        r'\bindiranagar\b',
    ),
    (
        "https://cafe.bluetokaicoffee.com/koramangala-bengaluru-36832/home",
        "Blue Tokai Coffee Roasters Koramangala, 5th Block",
        r'\b5th block\b',
    ),
    (
        "https://cafe.bluetokaicoffee.com/koramangala-bengaluru-33591/home",
        "Blue Tokai Coffee Roasters Koramangala",
        r'\bkoramangala\b',
    ),
    (
        "https://cafe.bluetokaicoffee.com/bangalore-east-taluk-bengaluru-34283/home",
        "Blue Tokai Coffee Roasters RMZ Ecoworld",
        r'\brmz\b',
    ),
    (
        "https://cafe.bluetokaicoffee.com/hsr-layout-bengaluru-33594/home",
        "Blue Tokai Coffee Roasters HSR Layout",
        r'\bhsr\b',
    ),
    (
        "https://cafe.bluetokaicoffee.com/jayanagar-bengaluru-33595/home",
        "Blue Tokai Coffee Roasters JP Nagar",
        r'\bjp nagar\b',
    ),
]

HEADERS = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
}


def fetch_html():
    conn = http.client.HTTPSConnection("bluetokaicoffee.com")
    conn.request("GET", "/pages/events-new", headers=HEADERS)
    return conn.getresponse().read()


def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select('div[location*="Bengaluru"] a[href*="/products"]')
    return [link.get("href") for link in links]


def fetch_product_json(slug):
    conn = http.client.HTTPSConnection("bluetokaicoffee.com")
    conn.request("GET", f"/products/{slug}.json", headers=HEADERS)
    r = conn.getresponse().read()
    return json.loads(r)


def find_bengaluru_variant(product_json):
    for variant in product_json["product"]["variants"]:
        if "Bengaluru" in variant["title"]:
            dates = list(datefinder.find_dates(variant["title"]))
            if len(dates) == 1:
                return variant, dates[0]
    return None, None

def extract_timing(body_html):
    clean_text = BeautifulSoup(body_html, "html.parser").get_text()
    # Find timings like "12 PM - 2 PM", allowing for variable spacing
    timing_match = re.search(r"(\d{1,2})\s*(AM|PM)\s*-\s*(\d{1,2})\s*(AM|PM)", clean_text, re.IGNORECASE)
    if timing_match:
        start_hour, start_period, end_hour, end_period = timing_match.groups()
        # Convert to 24-hour format
        start_hour = int(start_hour) % 12 + (12 if start_period.upper() == "PM" else 0)
        end_hour = int(end_hour) % 12 + (12 if end_period.upper() == "PM" else 0)
        return start_hour, end_hour
    return None


def guess_location(body_html):
    body_text = BeautifulSoup(body_html, "html.parser").get_text()
    for line in body_text.split("\n"):
        if "Bengaluru" in line:
            for location in LOCATIONS:
                if re.search(location[2], line, re.IGNORECASE):
                    return (location[0], location[1])


def generate_event_object(product_json, variant, date, start_hour, end_hour):
    tz = timezone(timedelta(hours=5, minutes=30))
    start_datetime = datetime(
        date.year, date.month, date.day, start_hour, 0, tzinfo=tz
    )
    end_datetime = datetime(
        date.year, date.month, date.day, end_hour, 0, tzinfo=tz
    )
    (location_url, address) = guess_location(product_json["product"]["body_html"])
    event = {
        "url": f"https://bluetokaicoffee.com/products/{product_json['product']['handle']}",
        "name": product_json["product"]["title"],
        "description": BeautifulSoup(
            product_json["product"]["body_html"], "html.parser"
        ).get_text(),
        "startDate": start_datetime.isoformat(),
        "endDate": end_datetime.isoformat(),
        "image": product_json["product"]["image"]["src"],
        "offers": {
            "@type": "Offer",
            # convert price to integer without decimal point ("850.00" -> "850")
            "price": str(ceil(float(variant["price"]))),
            "priceCurrency": "INR",
        },
        "location": {
            "@type": "Place",
            "name": address,
            "url": location_url,
            "address": address + " Bengaluru",
        }
    }
    return event


def main():
    html = fetch_html()
    links = parse_html(html)
    events = []
    for link in links:
        slug = link.split("/")[-1].split("#")[0]
        product_json = fetch_product_json(slug)
        variant, date = find_bengaluru_variant(product_json)
        if variant and date:
            (start_hour, end_hour) = extract_timing(product_json["product"]["body_html"])
            event = generate_event_object(product_json, variant, date, start_hour, end_hour)
            events.append(event)

    with open("out/bluetokai.json", "w") as f:
        json.dump(events, f, indent=2)


if __name__ == "__main__":
    main()
