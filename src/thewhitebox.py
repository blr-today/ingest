import datefinder
import json
from datetime import datetime
from common.tz import IST
from common.shopify import Shopify, ShopifyProduct, ShopifyVariant

DOMAIN = 'thewhiteboxco.in'
COLLECTION = 'events-of-the-month'

# Convert variants to Schema.org/Offer
def make_offers(product: ShopifyProduct):
    return [
        {
            "@type": "Offer",
            "priceCurrency": "INR",
            "price": variant.price,
        }
        for variant in product.variants
    ]

# Some events happen at multiple cities on different dates.
# Check if bangalore is mentioned in any variant if not return the first variant's title
def bangalore_variant(variants: ShopifyVariant):
    for variant in variants:
        if 'bangalore' in variant.title.lower() or 'bengaluru' in variant.title.lower():
            return variant.title

    return variants[0].title

# Fetch timings from the variant.title. It returns start_date and end_date timestamps
def fetch_timings(date_str: str):
    date_parts = date_str.split(" | ")

    # date_part is not always at fixed position in the title
    # format 1: "Saturday - Aug 24 | 4-6 PM | Nolte India"
    # format 2: "Lady’s Pass / BANGALORE | October 27 | 4-6 PM | Jamming Goat"
    # We use datefinder coz it finds the closest year automatically
    for month in ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']:
        if month in date_parts[0]:
            date_part = date_parts[0]
            time_part = date_parts[1]
            break
        else:
            date_part = date_parts[1]
            time_part = date_parts[2]

    event_date = list(datefinder.find_dates(date_part))[0]

    if len(date_parts) < 2:
        print(f"Failed parsing {date_str}")
        raise ValueError("Could not find time in" + date_str)

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


def make_event(product, sp: Shopify):
    start_date, end_date = fetch_timings(bangalore_variant(product.variants))

    return {
        "name": product.title,
        "description": product.description,
        "url": product.url,
        "offers": make_offers(product),
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
    }


# Ignore "TO BE ANNOUNCED" events
def filter_products(products):
    return filter(
        lambda p: any("to be announced" not in v.title.lower() for v in p.variants),
        products,
    )

# Events include past events as well. Filter only future events
def filter_future_events(events):
    current_time = datetime.now().isoformat()
    for event in events:
        if event['startDate'] < current_time:
            events.remove(event)

    return events


if __name__ == "__main__":
    from common.session import get_cached_session
    session = get_cached_session()
    white_box = Shopify(DOMAIN, session, COLLECTION)
    events = [make_event(p, white_box) for p in filter_products(white_box.products())]
    events = filter_future_events(events)
    with open("out/thewhitebox.json", "w") as f:
        json.dump(events, f, indent=2)
        print(f"[THEWHITEBOX] {len(events)} events")
