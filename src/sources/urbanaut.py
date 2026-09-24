import json
from common.session import get_cached_session
from bs4 import BeautifulSoup
import datetime
from common.tz import IST
import time

"""Public API key for search-v2, the typesense host urbanaut moved to"""
TYPESENSE_API_KEY = "NSUWIvHiEDI8jvLN2GLhTfCzg3T6oYYV"
SEARCH_URL = "https://search-v2.urbanaut.app/multi_search"
BASE_IMAGE_URL = "https://d10y46cwh6y6x1.cloudfront.net"
"""
urbanaut supports hosts, which are not necessarily venues
in case a host is also the venue
we can use the host name as the venue name
so we keep a list of such host slugs or names
"""
KNOWN_HOST_VENUES = [
    "Bento Bento",
    "copperandcloves",
    "courtyard",
    "loveooru",
    "printingwithtypes",
    "cafeplume",
    "museum-of-art-and-photography-map",
    "ksaraah",
    "flourishclasses",  # Flourish Bakery
]
session = get_cached_session()


def parse_date(date_str):
    return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)


def scrape_urbanaut(category_name="Events"):
    ts = int(time.time())

    headers = {"x-typesense-api-key": TYPESENSE_API_KEY}
    search = {
        "collection": "spots",
        "q": "*",
        "query_by": "name",
        "page": 1,
        "per_page": 100,
        "filter_by": f"enable_list_view:=true && city:=Bengaluru && category_data.name:=[{category_name}] && (end_timestamp:>={ts} || has_end_timestamp:false )",
        "sort_by": "order:asc",
    }

    resp = session.post(SEARCH_URL, headers=headers, json={"searches": [search]})
    return resp.json()["results"][0]


def get_slots(slug):
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    one_year_later = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime(
        "%Y-%m-%d"
    )
    url = f"https://urbanaut.app/api/v3/spot/approved/booking/data/{slug}/?after={today_date}&before={one_year_later}"
    data = session.get(url).json()
    return [item for sublist in data["dates"] for item in sublist["slots"]]


def get_age_range(x):
    audience = " ".join([y["path"] for y in x.get("who_is_it_for_tag", [])]).lower()
    """
    Urbanaut marks these events with 18+
    but drinking age in BLR is 21
    and these are typically gated because of drinks
    """
    if "adults_only" in audience:
        return "21+"
    elif "kid_friendly" in audience:
        return "2-"
    elif "for_all_ages" in audience:
        return "5+"
    elif "for_couples" in audience:
        return "16+"
    else:
        return "12+"


def get_event_type(x):
    tags = " ".join([y["path"] for y in x.get("genre_tag", [])]).lower()
    name = x["name"].lower()
    if "screening" in name:
        return "ScreeningEvent"
    elif "food" in tags or "araku" in name:
        return "FoodEvent"
    elif "workshop" in tags:
        return "EducationEvent"
    else:
        return "Event"


def get_keywords(x):
    base = [y["name"] for y in x.get("genre_tag", [])]
    if x.get("account_slug") == "courtyard":
        base += ["COURTYARD"]
    return base + ["URBANAUT"]


def make_event(x):
    desc = BeautifulSoup(x["short_description"], "html.parser").text

    slots = get_slots(x["slug"])

    available_slot_count = sum([slot["available"] > 0 for slot in slots])
    for slot in slots:
        if slot["available"] > 0:
            # In case there are multiple slots, we want to put a slug at the end
            # to differentiate between events
            url = f"https://urbanaut.app/spot/{x['slug']}"
            if available_slot_count > 1:
                url += "#" + parse_date(slot["start"]).strftime("%Y-%m-%dT%H%M")

            yield {
                "@context": "https://schema.org",
                "@type": get_event_type(x),
                "name": x["name"],
                "description": desc,
                "image": [BASE_IMAGE_URL + "/" + y["path"] for y in x["medias"]],
                "startDate": parse_date(slot["start"]).isoformat(),
                "endDate": parse_date(slot["end"]).isoformat(),
                "location": {
                    "@type": "Place",
                    "name": (
                        x["company_name"]
                        if (
                            x.get("account_slug") in KNOWN_HOST_VENUES
                            or x.get("company_name") in KNOWN_HOST_VENUES
                        )
                        else None
                    ),
                    "address": x["address"],
                    "url": f"https://www.google.com/maps/search/?api=1&query=Google&query_place_id={x['google_place_id']}"
                    if x.get("google_place_id")
                    else None,
                    "latitude": x["lat"],
                    "longitude": x["lng"],
                },
                "eventAttendanceMode": "OfflineEventAttendanceMode",
                "eventStatus": "EventScheduled",
                "maximumAttendeeCapacity": slot["total"],
                "remainingAttendeeCapacity": slot["available"],
                "typicalAgeRange": get_age_range(x),
                "offers": {
                    "@type": "Offer",
                    "price": x["price_starts_at"],
                    "availability": "LimitedAvailability",
                    "priceCurrency": x.get("price_starts_at_currency", "INR"),
                },
                "organizer": {
                    "@type": "Organization",
                    "name": x["company_name"],
                    "description": x.get("company_description"),
                    "url": f"https://urbanaut.app/partner/{x['account_slug']}"
                    if "account_slug" in x
                    else None,
                    "image": BASE_IMAGE_URL + "/" + x["logo_path"],
                },
                "url": url,
                "keywords": get_keywords(x),
            }


if __name__ == "__main__":
    events = []
    with open("out/urbanaut.json", "w") as f:
        for x in scrape_urbanaut()["hits"]:
            for event in make_event(x["document"]):
                events.append(event)
        json.dump(events, f, indent=2)
        print(f"[URBANAUT] {len(events)} events")
