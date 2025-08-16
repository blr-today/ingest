import requests
import json
from bs4 import BeautifulSoup
import re
from datetime import datetime
import datefinder
from common.tz import IST
from math import ceil
from common.session import get_cached_session
from common import USER_AGENT_HEADERS as HEADERS

LOCATIONS = [
    (
        "https://cafe.bluetokaicoffee.com/sarvagna-nagar-bengaluru-34817/home",
        "Blue Tokai Coffee Roasters HRBR Layout",
        r"\bhrbr\b",
        13.024729,
        77.639929
    ),
    (
        "https://cafe.bluetokaicoffee.com/jayanagar-bengaluru-34903/home",
        "Blue Tokai Coffee Roasters Jayanagar",
        r"\bjayanagar\b",
        13.024729,
        77.639929
    ),
    (
        "https://cafe.bluetokaicoffee.com/armane-nagar-bengaluru-34815/home",
        "Blue Tokai Coffee Roasters Sadashiva Nagar",
        r"\bsadashiva\b",
        13.006963967543491,
        77.57904497534919
    ),
    (
        "https://cafe.bluetokaicoffee.com/mahadevapura-bengaluru-33593/home",
        "Blue Tokai Coffee Roasters Whitefield",
        r"\bwhitefield\b",
        12.99609493,
        77.6954406
    ),
    (
        "https://bluetokaicoffee.com/pages/blue-tokai-coffee-roasters-ub-city-bangalore",
        "Blue Tokai Coffee Roasters UB City",
        r"\bub city\b",
        12.9717222,
        77.59425
    ),
    # This is not a cafe but their Roastery itself
    (
        "https://maps.app.goo.gl/fssZvwfXuxhaC7G77",
        "Blue Tokai Roastery, NGEF Layout",
        r"\bngef\b",
    ),
    (
        "https://cafe.bluetokaicoffee.com/shivaji-nagar-bengaluru-33592/home",
        "Blue Tokai Coffee Roasters Infantry Road",
        r"\binfantry\b",
        12.98112721,
        77.60339846
    ),
    (
        "https://cafe.bluetokaicoffee.com/indiranagar-bengaluru-34282/home",
        "Blue Tokai Coffee Roasters Indiranagar, Domlur",
        r"\bdomlur\b",
    ),
    (
        "https://cafe.bluetokaicoffee.com/indiranagar-bengaluru-33590/home",
        "Blue Tokai Coffee Roasters Indiranagar",
        r"\bindiranagar\b",
        12.967299,
        77.636701
    ),
    (
        "https://cafe.bluetokaicoffee.com/koramangala-bengaluru-36832/home",
        "Blue Tokai Coffee Roasters Koramangala, 5th Block",
        r"\b5th block\b",
        12.9661571,
        77.662065

    ),
    (
        "https://cafe.bluetokaicoffee.com/koramangala-bengaluru-33591/home",
        "Blue Tokai Coffee Roasters Koramangala",
        r"\bkoramangala\b",
        12.94098007,
        77.62012452
    ),
    (
        "https://cafe.bluetokaicoffee.com/bangalore-east-taluk-bengaluru-34283/home",
        "Blue Tokai Coffee Roasters RMZ Ecoworld",
        r"\brmz\b",
        12.920362546335918,
        77.68606341873948
    ),
    (
        "https://cafe.bluetokaicoffee.com/hsr-layout-bengaluru-33594/home",
        "Blue Tokai Coffee Roasters HSR Layout",
        r"\bhsr\b",
        12.91279211,
        77.64475762
    ),
    (
        "https://cafe.bluetokaicoffee.com/jayanagar-bengaluru-33595/home",
        "Blue Tokai Coffee Roasters JP Nagar",
        r"\bjp nagar\b",
        12.90694327,
        77.59912373
    ),
    (
        "https://bluetokaicoffee.com/pages/blue-tokai-coffee-roasters-aecs-layout",
        "Blue Tokai Coffee Roasters AECS Layout",
        r"\baecs\b",
        12.9633889,
        77.7095833
    )
]


def fetch_html():
    session = get_cached_session()
    response = session.get(
        "https://bluetokaicoffee.com/pages/coffee-workshop-events", headers=HEADERS
    )
    return response.text


def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select('div[location*="Bengaluru"] a[href*="/products"]')
    return [link.get("href") for link in links]


def fetch_product_json(slug):
    session = get_cached_session()
    response = session.get(
        f"https://bluetokaicoffee.com/products/{slug}.json", headers=HEADERS
    )
    return response.json()


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
    timing_match = re.search(
        r"(\d{1,2})\s*(AM|PM)\s*-\s*(\d{1,2})\s*(AM|PM)", clean_text, re.IGNORECASE
    )
    if timing_match:
        start_hour, start_period, end_hour, end_period = timing_match.groups()
        start_hour = int(start_hour) % 12 + (12 if start_period.upper() == "PM" else 0)
        end_hour = int(end_hour) % 12 + (12 if end_period.upper() == "PM" else 0)
        # Sometimes we get a listing like Time: 11 PM - 4 PM 
        if start_hour > end_hour:
            start_hour -= 12
        return start_hour, end_hour
    else:
        timing_match = re.search(
            r"(\d{1,2})\s+(AM|PM)", clean_text, re.IGNORECASE
        )
        if timing_match:
            start_hour, start_period = timing_match.groups()
            start_hour = int(start_hour) % 12 + (12 if start_period.upper() == "PM" else 0)
            # Default end hour to 2 hours later
            end_hour = (start_hour + 2) % 24
            return start_hour, end_hour
    return None

def guess_location(body_html):
    body_text = BeautifulSoup(body_html, "html.parser").get_text()
    for line in body_text.split("\n"):
        if "Bengaluru" in line or "Koramangala" in line or "Blue Tokai Coffee Roasters" in line:
            for location in LOCATIONS:
                if re.search(location[2], line, re.IGNORECASE):
                    return (location[0], location[1], location[3], location[4])


def generate_event_object(product_json, variant, date, start_hour, end_hour):
    start_datetime = datetime(
        date.year, date.month, date.day, start_hour, 0, tzinfo=IST
    )
    end_datetime = datetime(date.year, date.month, date.day, end_hour, 0, tzinfo=IST)
    location = guess_location(product_json["product"]["body_html"])
    if not location:
        print(f"[BLUETOKAI] Could not find a location in BLR: https://bluetokaicoffee.com/products/{product_json['product']['handle']}")
        return None
    (location_url, address, lat, lng) = location

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
            "geo": {
                "@type": "GeoCoordinates",
                "latitude": lat,
                "longitude": lng,
            }
        },
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
            (start_hour, end_hour) = extract_timing(
                product_json["product"]["body_html"]
            )
            event = generate_event_object(
                product_json, variant, date, start_hour, end_hour
            )
            if event:
                events.append(event)
    with open("out/bluetokai.json", "w") as f:
        json.dump(events, f, indent=2)
    print(f"[BLUETOKAI] {len(events)} events")


if __name__ == "__main__":
    main()
