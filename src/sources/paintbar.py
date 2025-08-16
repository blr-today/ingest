import datefinder
import json
from datetime import datetime
from common.tz import IST
from common.shopify import Shopify, ShopifyProduct

DOMAIN = 'www.paintbar.in'
COLLECTION = 'paint-bar-bangalore'

# Convert variants to Schema.org/Offer
def make_offers(product: ShopifyProduct):
    return [
        {
            "@type": "Offer",
            "priceCurrency": "INR",
            "price": variant.price,
            "name": variant.title
        }
        for variant in product.variants
    ]

# Fetch timings from the variant.title. It returns start_date and end_date timestamps
def fetch_timings(date_str: str):
    parts = date_str.split(" | ")
    date_part = parts[-2]
    time_part = parts[-1]

    event_date = list(datefinder.find_dates(date_part))[0]

    for splitter in ["to", "-"]:
        if splitter in time_part:
            l = [x.strip() for x in time_part.split(splitter)]

    if l == None:
        raise ValueError("Could not find time in" + date_str)

    known_twelveness = [
        twelveness for twelveness in ["am", "pm"] for i in l if twelveness in i
    ]

    timestamps = []

    for time_str in l:
        # check if time_str contains AM or PM
        if not ("am" in time_str or "pm" in time_str):
            time_str += known_twelveness[0]
        timestamps.append(
            list(datefinder.find_dates(time_str, base_date=event_date))[0].replace(
                tzinfo=IST
            )
        )

    if len(timestamps) != 2:
        raise ValueError("Could not find time in" + date_str)

    return timestamps

def make_name(title):
    return " | ".join(title.split(" | ")[:-2]).strip()

def make_event(product, sp: Shopify):
    start_date, end_date = fetch_timings(product.title)

    return {
        "name": make_name(product.title),
        "description": product.description,
        "url": product.url,
        "offers": make_offers(product),
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
    }

if __name__ == "__main__":
    from common.session import get_cached_session
    session = get_cached_session()
    paint_bar = Shopify(DOMAIN, session, COLLECTION)
    events = [make_event(p, paint_bar) for p in paint_bar.products()]

    with open("out/paintbar.json", "w") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
        print(f"[PAINTBAR] {len(events)} events")
