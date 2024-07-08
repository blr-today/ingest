from extruct.jsonld import JsonLdExtractor
from bs4 import BeautifulSoup
from datetime import timedelta, datetime
from common.session import get_cached_session
import datefinder
import json
from common.tz import IST

BASE_URL = "https://troveexperiences.com/"

# TODO: Move to TEST
# Input dates
dates = [
    "Sat | Jun 29 | 10 AM - 12:30 PM",
    "Sat | Jun 29 | 3 - 6 PM",
    "Sun | Jun 30 | 9:30 -11:30 AM",
    "Sun | Jun 30 | 11 AM - 1 PM",
    "Sat | Jul 06 | 4 - 6:30 PM",
    "Sun | Jul 07 | 8:30 AM to 11:30 AM",
    "Sun | Jul 07 | 10 AM to 12:30 PM",
    "Sun | Jul 14 | 10:30 AM - 1 PM",
    "Sun | Jul 14 | 4 - 7 PM",
]

TIME_FORMAT_STRINGS = ["%I %p", "%I%p", "%I:%M %p", "%I:%M%p"]


def scrape_trove(location):
    session = get_cached_session()

    url = f"https://troveexperiences.com/collections/upcoming/{location}"
    soup = BeautifulSoup(session.get(url).content, "html.parser")
    for link in soup.select("a.grid-product__link"):
        url = BASE_URL + link["href"]
        r = session.get(url)
        soup = BeautifulSoup(r.text, "html.parser")
        date_str = soup.select_one('form div.variant-input input[type="radio"]')[
            "value"
        ]
        startDate, endDate = parse_date(date_str)
        location_text = soup.select_one(".custom-field__location").text

        data = JsonLdExtractor().extract(r.text)

        product = list(filter(lambda x: x["@type"] == "Product", data))[0]
        if "InStock" in product["offers"][0]["availability"]:
            yield {
                "offers": product["offers"],
                "name": product["name"],
                "description": product["description"],
                "url": product["url"],
                "startDate": startDate.isoformat(),
                "endDate": endDate.isoformat(),
                "image": product["image"],
                "location": location_text,
            }


def parse_time(time_str):
    for fmt in TIME_FORMAT_STRINGS:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            pass


def parse_date(date_str):
    date = date_str.split(" | ")[1]
    # We use datefinder coz it finds the closest year automatically
    event_date = list(datefinder.find_dates(date))[0]
    time_part = date_str.split(" | ")[2]
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


if __name__ == "__main__":
    events = []
    for event in scrape_trove("bangalore"):
        events.append(event)
    with open("out/trove.json", "w") as f:
        json.dump(events, f, indent=2)
