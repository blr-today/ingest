import datefinder
import json
from bs4 import BeautifulSoup
from common.tz import IST
from common.shopify import Shopify, ShopifyProduct, ShopifyVariant

DOMAIN = "troveexperiences.com"
COLLECTION = "bangalore"


# Convert variants to Schema.org/Offer
def make_offers(product: ShopifyProduct):
    return [
        {
            "@type": "Offer",
            "priceCurrency": "INR",
            "price": variant.price,
            "sku": variant.sku,
        }
        for variant in product.variants
    ]


# Fetch timings from the variant.title. It returns start_date and end_date timestamps
def fetch_timings(date_str: str):
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


def get_subtitle(soup):
    subtitle = soup.select_one(".custom-field__sub-title")
    if not subtitle:
        return None
    return subtitle.get_text(strip=True)


def get_location(soup):
    location_field = soup.select_one(".custom-field__location")
    if not location_field:
        return None
    location_name = location_field.get_text(strip=True)
    if not location_name or len(location_name) == 0:
        return None
    if "," in location_name:
        s = location_name.split(",")
        return (s[0].strip(), ",".join(s[1:]).strip())
    return (location_name, None)


def make_event(product, sp: Shopify, session):
    start_date, end_date = fetch_timings(product.variants[0].title)

    res = session.get(product.url)
    soup = BeautifulSoup(res.text, "html.parser")

    location_name, address = get_location(soup)
    subtitle = get_subtitle(soup)

    res = {
        "name": product.title,
        "description": product.description,
        "url": product.url,
        "offers": make_offers(product),
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
    }

    if subtitle:
        res["name"] += f" - {subtitle}"

    if location_name:
        res["location"] = {"@type": "Place", "name": location_name}
        if address:
            res["location"]["address"] = address
    return res


# Ignore "Coming Soon" events
def filter_products(products):
    return filter(
        lambda p: any("coming soon" not in v.title.lower() for v in p.variants),
        products,
    )


if __name__ == "__main__":
    from common.session import get_cached_session

    session = get_cached_session()
    trove = Shopify(DOMAIN, session, COLLECTION)
    events = [
        make_event(product, trove, session)
        for product in filter_products(trove.products())
    ]
    with open("out/trove.json", "w") as f:
        json.dump(events, f, indent=2)
        print(f"[TROVE] {len(events)} events")
