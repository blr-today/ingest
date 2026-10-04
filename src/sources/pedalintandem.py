import json
from datetime import date, datetime, timedelta
from curl_cffi import requests
from common.jev import ask, clock, end_clock, time_questions
from typesafe_sdk import TypeSafeClient
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.pedalintandem.com"
BLR_LOCATIONS = [
    "bangalore",
    "bengaluru",
    "arkavathi",
    "avalahalli",
    "avathi",
    "devarayanadurga",
    "gunjur",
    "hennur",
    "Hesaraghatta",
    "kanakapura",
    "malleshwaram",
    "indiranagar",
    "manchanabele",
    "pedal",
    "pitstop",
    "rajankunte",
    "nandi",
    "melagiri",
]


def fetch_events_links(session):
    res = session.get(f"{BASE_URL}/experiences")
    soup = BeautifulSoup(res.text, "html.parser")
    events = soup.select("div.single-experience")

    return map(lambda x: x.find("a")["href"], events)


def fetch_events(event_links, session):
    events = []

    for event_link in event_links:
        url = f"{BASE_URL}{event_link}"
        event_page = session.get(url)
        event = BeautifulSoup(event_page.text, "html.parser")
        location = event.select_one("div.location").get_text().strip().lower()

        date_selector = event.select_one("div.product-variations-varieties select")

        # Fetch data of the events which would be happening in future otherwise skip
        if "disabled" in date_selector.attrs:
            continue

        # Select only single day event. Multi day events are in the format "2D/ 3N"
        duration = event.select_one("div.duration").get_text().strip()
        if bool(re.search("/", duration)):
            print(
                f"[PIT] {event_link} is {duration} long, assuming MULTIDAY and ignoring"
            )
            continue

        # Skip if location is not in bangalore
        inside_blr = False
        for place_inside_blr in BLR_LOCATIONS:
            if place_inside_blr in location.lower():
                inside_blr = True

        if not inside_blr:
            print(f"[PIT] {event_link} {location} not in BLR")
            continue

        # Pass url so that it can be added in event
        events.append([event, event_link])

    return events


def make_event(soup, client):
    event = soup[0]
    url = soup[1]

    heading = event.select_one("div.heading").get_text().strip()

    location = find_location(event)

    offers_selector = event.select_one("div.cart-details")

    duration = event.select_one("div.duration").get_text().strip()
    duration_in_hours = convert_duration_in_hours(duration)

    date_opts = offers_selector.select(
        'div.product-variations-variety select[name="variety_id"] option'
    )
    days = sorted(
        {
            datetime.strptime(opt.get_text().strip(), "%d-%b-%Y").date()
            for opt in date_opts
            if "data-booking-begin-at" in opt.attrs
        }
    )
    days = [d for d in days if d >= date.today()]
    if not days:
        raise ValueError("no upcoming dates")

    itinerary = event.select_one("div.text-box div.trix-content")
    state = {
        "ride": heading,
        "duration": duration,
        "itinerary": itinerary.get_text("\n", strip=True) if itinerary else "",
        "description": event.select_one("div.trix-content div").get_text(
            "\n", strip=True
        ),
    }
    nouls, picks = ask(client, state, time_questions("the ride or session"))
    start = clock(picks, "start")
    if not start:
        raise ValueError("no start time")
    end = end_clock(nouls, picks)
    length = timedelta(hours=duration_in_hours or 2)

    offers = get_offers(offers_selector)

    # details
    metrics = {}
    event_metrics = event.select("div.single-metric.active div.content")

    for event_metric in event_metrics:
        title = event_metric.find("p").get_text().strip()
        value = event_metric.find("h3").get_text().strip()
        metrics[title] = value

    description = event.select_one("div.trix-content div").get_text()

    events = []
    for day in days:
        begin = datetime.combine(day, start)
        events.append(
            {
                "@context": "https://schema.org",
                "@type": "SportsEvent",
                "name": heading,
                "sports": "Cycling",
                "location": location,
                "offers": offers,
                "startDate": begin.isoformat(),
                "endDate": (
                    datetime.combine(day, end) if end else begin + length
                ).isoformat(),
                "description": process_description(description) + "\n" + str(metrics),
                "url": BASE_URL + url + (f"#{day}" if len(days) > 1 else ""),
                "keywords": [url.split("/")[2], "PEDALINTANDEM"],
            }
        )
    return events


def find_location(soup):
    location = {"@type": "Place"}
    address = None

    SELECTORS = [
        (
            "div.text-box div.trix-content li",
            [
                r"meet\s+at\s+([^,]+),",
                r"meeting\s+point(?:[^:]*?):\s+([^.]+)(?:\.|\n|$)",
            ],
        ),
        (
            "div.description div.description-style div.trix-content div",
            [r"location(?:[^:]*?):\s+([^.]+)(?:\.|\n|$)"],
        ),
        ("div.location", [r"(.*)"]),
    ]

    address = None
    for css_selector, regex_patterns in SELECTORS:
        element = soup.select_one(css_selector)
        if not element:
            continue

        text = element.get_text().lower().strip()

        for pattern in regex_patterns:
            matches = re.search(pattern, text)
            if matches:
                address = matches.group(1).strip()
                break

        if address:
            break

    if address.lower() == "pedal in tandem" or "indiranagar" in address.lower():
        location["address"] = (
            "837/1, 2nd Cross, 7th Main, 2nd Stage, Indiranagar, Bengaluru, Karnataka"
        )
        location["name"] = "Pedal in Tandem"
    else:
        location["address"] = address
    return location


def convert_duration_in_hours(duration):
    duration_range = duration.split(",")[0]

    # Duration either has a range or fixed no. of hours.
    for hour in ["hours", "hrs"]:
        if hour in duration_range:
            duration_range = duration_range.replace(hour, "")

            for splitter in ["to", "-"]:
                if splitter in duration_range:
                    return int(duration_range.split(splitter)[1].strip())

            return int(duration_range.strip())

    return 0


def get_offers(soup):
    offers = []
    addOns = []

    opts = soup.select('div.product-variations select[name="variation_id"] option')
    for opt in opts:
        offer = {"priceCurrency": "INR", "@type": "offer"}
        opt_name = opt.get_text().lower()
        price = opt["data-price-after-discount"]
        price = price.replace("\u20b9", "").replace(",", "")
        if "rent" in opt_name or "transport" in opt_name:
            addOn = {"@type": "offer"}
            addOn["name"] = opt_name
            addOn["price"] = price
            addOn["priceCurrency"] = "INR"
            addOns.append(addOn)
        else:
            offer["name"] = opt_name
            offer["price"] = price
            offers.append(offer)

    if len(addOns) != 0:
        offers.append(addOns)

    return offers


def process_description(description):
    # Remove chain of hyphen '-' and convert it into a newline
    processed_text = re.sub(r"-{2,}", "\n", description)
    processed_text = processed_text.replace("\u00a0", "\n")
    return processed_text


def main():
    session = requests.Session()
    event_links = fetch_events_links(session)
    events_data = fetch_events(event_links, session)

    events = []
    with TypeSafeClient() as client:
        for event_data in events_data:
            try:
                events.extend(make_event(event_data, client))
            except ValueError as e:
                print(f"[PIT] {event_data[1]} skipped, {e}")

    with open("out/pedalintandem.json", "w") as f:
        json.dump(events, f, indent=2)


if __name__ == "__main__":
    main()
