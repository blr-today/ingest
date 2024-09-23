from bs4 import BeautifulSoup
import datefinder
import json

from common.tz import IST
from common import shopifyproducts

BASE_URL = 'https://troveexperiences.com/'
collection = 'collections/bangalore'

# Check product variants. If it is coming soon, there is no date, skip. Otherwise it will have date in title
def filter_data(products):
    data = []
    for product in products:
        for variant in product['variants']:
            if variant['title'] != 'Coming Soon!':
                data.append(product)
                break
    return data

# Fetch offers from variants.
def fetch_offers(product):
    variants = product['variants']
    offers = []

    for variant in variants:
        offer = {
        '@type': 'Offer',
        'priceCurrency': 'INR',
        'price': variant['price'],
        'sku': variant['sku'],
        'url': f"{BASE_URL}{collection}/products/{product['handle']}",
        }

        offers.append(offer)

    return offers

# Fetch timings from the variant.title. It returns start_date and end_date timestamps
def fetch_timings(variants):
    date_str = variants[0]['title']

    date_parts = date_str.split(" | ")
    # We use datefinder coz it finds the closest year automatically
    event_date = list(datefinder.find_dates(date_parts[1]))[0]
    if len(date_parts) < 3:
        print(f"Failed parsing {date_str}")
        raise ValueError("Could not find time in" + date_str)
    time_part = date_parts[2]
    for splitter in ["to", "-"]:
        if splitter in time_part:
            l = [x.strip() for x in time_part.split(splitter)]

    if l == None:
        raise ValueError("Could not find time in" + date_str)

    known_twelveness = [
        twelveness for twelveness in ["AM", "PM"] for i in l if twelveness in i
    ]

    timestamps = []

    for time_str in l:
        # check if time_str contains AM or PM
        if not ("AM" in time_str or "PM" in time_str):
            time_str += known_twelveness[0]
        timestamps.append(
            list(datefinder.find_dates(time_str, base_date=event_date))[0].replace(
                tzinfo=IST
            )
        )

    if len(timestamps) != 2:
        raise ValueError("Could not find time in" + date_str)

    return timestamps

def fetch_description(product):
    description = BeautifulSoup(product['body_html'], 'html.parser').get_text()
    description = description.replace('\u00a0', "\n")
    description = description.replace('\u2014', '-')
    description = description.replace('\u2019', "'")
    return description

def make_event(product):
    start_date, end_date = fetch_timings(product['variants'])
    duration = end_date.hour - start_date.hour

    return {
        "@context": "https://schema.org",
        "@type": "Event",
        'about': product['title'],
        'description': fetch_description(product),
        'url': f"{BASE_URL}{collection}/products/{product['handle']}",
        'keywords': product['tags'],
        'offers': fetch_offers(product),
        'duration': duration,
        'startDate': start_date.isoformat(),
        'endDate': end_date.isoformat()
    }

if __name__ == "__main__":
    sp = shopifyproducts.ShopifyProducts(BASE_URL, collection)
    products = filter_data(sp.fetch_products())
    
    events = list(map(make_event, products))
    output_json_file = "out/trove.json"
    with open(output_json_file, "w") as f:
        json.dump(events, f, indent=2)
