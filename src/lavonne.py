import json
from datetime import datetime
from bs4 import BeautifulSoup
from common.tz import IST

URL = "https://www.lavonne.in/courses/short-term/weekend-calendar/"


def parse_time_range(time_str, base_date):
    """Parse time range like '10:00 am to 1:00 pm' and attach to base_date"""
    start_time, end_time = time_str.split(" to ")

    # Parse start time
    start = datetime.strptime(f"{base_date} {start_time}", "%Y%m%d %I:%M %p")
    start = start.replace(tzinfo=IST)

    # Parse end time
    end = datetime.strptime(f"{base_date} {end_time}", "%Y%m%d %I:%M %p")
    end = end.replace(tzinfo=IST)

    return start, end


def parse_event(event_div):
    """Parse a single weekend course div into an event dict"""
    date_str = event_div["data-date"]  # Format: YYYYMMDD

    # Get basic info
    title = event_div.select_one("h3").text.strip()
    description_p = event_div.select_one(".small-8.medium-12.cell p").text.strip()

    # Get list items if they exist
    items = event_div.select(".small-8.medium-12.cell li")
    if items:
        items_text = "\n• " + "\n• ".join(item.text.strip() for item in items)
        description = description_p + items_text
    else:
        description = description_p

    # Get price
    price = event_div.select_one("dd span.large").text.strip()

    # Get time range
    time_range = event_div.select_one("dt:-soup-contains('Time') + dd").text.strip()
    start_time, end_time = parse_time_range(time_range, date_str)

    # Determine if it's an LBS (L Baking Studio) class
    is_lbs = "(LBS)" in title

    # Build the event object
    event = {
        "name": title,
        "description": description,
        "startDate": start_time.isoformat(),
        "endDate": end_time.isoformat(),
        "offers": {
            "@type": "Offer",
            "price": price,
            "priceCurrency": "INR"
        },
        "location": {
            "@type": "Place",
            "name": "L Baking Studio" if is_lbs else "Lavonne Academy",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "RMZ Ecoworld 30 Bhoganahalli, Bellandur" if is_lbs else "263, 3rd Cross Rd, Stage 2, Domlur",
                "addressLocality": "Bangalore",
                "addressRegion": "Karnataka",
                "addressCountry": "IN"
            }
        }
    }

    # Get registration URL if available
    register_link = event_div.select_one("a.success.button")
    if register_link and 'href' in register_link.attrs:
        event["url"] = register_link["href"]

    return event


def parse_lavonne_events(soup):
    events = []

    # Find all sections containing events
    sections = soup.find_all("div", class_="section")

    for section in sections:
        # Find all weekend course divs in this section
        course_divs = section.find_all("div", class_="weekend-course")

        for course_div in course_divs:
            event = parse_event(course_div)
            events.append(event)

    return events


if __name__ == "__main__":
    session = get_cached_session()
    response = session.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")

    events = parse_lavonne_events(soup)

    # Write output JSON file
    with open("out/lavonne.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
