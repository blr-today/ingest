import json
from common.session import get_cached_session
from bs4 import BeautifulSoup
import datetime
from common.tz import IST
import time

"""Public API Key used for searching events"""
TYPESENSE_API_KEY = "AYJefn98eRjmkyENmOlleSaqbXXQDKG6"
SEARCH_URL = "https://search.urbanaut.app/collections/spot_approved/documents/search?"
BASE_IMAGE_URL = "https://d10y46cwh6y6x1.cloudfront.net"
"""
urbanaut supports hosts, which are not necessarily venues
in case a host is also the venue
we can use the host name as the venue name
so we keep a list of such host slugs
"""
KNOWN_HOST_VENUES = [
    "copperandcloves",
    "courtyard",
    "loveooru",
    "printingwithtypes",
]
session = get_cached_session()


def parse_date(date_str):
    return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)


def scrape_urbanaut(categories="12"):
    ts = int(time.time())

    headers = {"x-typesense-api-key": TYPESENSE_API_KEY}
    querystring = {
        "q": "*",
        "page": "1",
        "per_page": "100",
        "filter_by": f"enable_list_view:=true && city:=Bengaluru && categories:=[{categories}] && (end_timestamp:>={ts} || has_end_timestamp:false )",
        "sort_by": "order:asc",
    }

    return session.get(SEARCH_URL, headers=headers, params=querystring).json()


def get_slots(slug):
    today_date = datetime.datetime.now().strftime("%Y-%m-%d")
    one_year_later = (datetime.datetime.now() + datetime.timedelta(days=365)).strftime(
        "%Y-%m-%d"
    )
    url = f"https://urbanaut.app/api/v3/spot/approved/booking/data/{slug}/?after={today_date}&before={one_year_later}"
    data = session.get(url).json()
    return [item for sublist in data["dates"] for item in sublist["slots"]]


def get_age_range(x):
    audience = " ".join([y["path"] for y in x["who_is_it_for_tags_data"]]).lower()
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
    tags = " ".join([y["path"] for y in x["genre_tags_data"]]).lower()
    name = x["name"].lower()
    if "screening" in name:
        return "ScreeningEvent"
    elif "food" in tags:
        return "FoodEvent"
    elif "workshop" in tags:
        return "EducationEvent"
    else:
        return "Event"


def get_keywords(x):
    base = [y["name"] for y in x["genre_tags_data"]]
    if x["account_data"]["slug"] == "courtyard":
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
                "image": [y["aws_url"] for y in x["medias"]],
                "startDate": parse_date(slot["start"]).isoformat(),
                "endDate": parse_date(slot["end"]).isoformat(),
                "location": {
                    "@type": "Place",
                    "name": (
                        x["account_data"]["company_name"]
                        if x["account_data"]["slug"] in KNOWN_HOST_VENUES
                        else None
                    ),
                    "address": x["address"],
                    "url": f"https://www.google.com/maps/search/?api=1&query=Google&query_place_id={x['google_place_id']}",
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
                    "priceCurrency": x["price_starts_at_currency"],
                },
                "organizer": {
                    "@type": "Organization",
                    "name": x["account_data"]["company_name"],
                    "description": x["account_data"]["company_description"],
                    "url": f"https://urbanaut.app/partner/{x['account_data']['slug']}",
                    "image": BASE_IMAGE_URL + x["account_data"]["logo_path"],
                    "contactPoint": {
                        "@type": "ContactPoint",
                        "telephone": x["account_data"]["company_phone"],
                    },
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
