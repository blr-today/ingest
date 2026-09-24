import requests
from common.tz import IST
import json
import datetime
import re

BASE_URL = "https://sistersinsweat.com"
CITY_PATH = "/bengaluru"
FUTURE_WINDOW = datetime.timedelta(days=90)
KNOWN_SPORTS = {
    "frisbee": "Frisbee",
    "pickleball": "Pickleball",
    "football": "Football",
    "basketball": "Basketball",
    "b'ball": "Basketball",
    "run ": "Running",
    "running": "Running",
    "baddy": "Badminton",
    "footy": "Football",
    "padel": "Pickeball",
}


def fetch_page(session, path):
    response = session.get(BASE_URL + path)
    response.raise_for_status()
    return response.text


# Page data ships as escaped JSON strings in Next.js self.__next_f.push() calls
def extract_rsc_text(html):
    chunks = re.findall(r"self\.__next_f\.push\(\[1,(\".*?\")\]\)", html, re.S)
    return "".join(json.loads(c) for c in chunks)


def extract_balanced_array(text, key):
    idx = text.find(f'"{key}":')
    if idx == -1:
        return None
    start = idx + len(key) + 3
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    return None


def clean(value):
    return None if value in (None, "$undefined") else value


def fetch_cards(session):
    text = extract_rsc_text(fetch_page(session, CITY_PATH))
    return extract_balanced_array(text, "cards") or []


def fetch_product_details(session, slug):
    text = extract_rsc_text(fetch_page(session, f"{CITY_PATH}/products/{slug}"))
    address_match = re.search(r'"rt-0-0",\{"children":"([^"]*)"\}', text)
    address = address_match.group(1) if address_match else None
    time_match = re.search(
        r'"text-sm font-semibold text-ink-dark","children":(\["[^\]]*\]|"[^"]*")',
        text,
    )
    end_time_text = None
    if time_match:
        value = json.loads(time_match.group(1))
        if isinstance(value, list) and len(value) == 2:
            end_time_text = value[1].strip(" –-")
    return address, end_time_text


def parse_end_time(start, end_time_text):
    try:
        end_time = datetime.datetime.strptime(end_time_text, "%I:%M %p").time()
    except ValueError:
        return None
    end = datetime.datetime.combine(start.date(), end_time, tzinfo=start.tzinfo)
    if end <= start:
        end += datetime.timedelta(days=1)
    return end


def guess_sport(card, slug):
    activity = clean(card.get("activityName"))
    if activity:
        return activity.strip().title()
    for key, value in KNOWN_SPORTS.items():
        if key in slug.lower():
            return value
    return None


def make_events(session, card):
    slug = card["slug"]
    title = card["title"]
    if "package-detail" in slug.lower():
        return []
    if any(word in title.lower() for word in ["subscription", "package"]):
        return []
    venue = clean(card.get("venueName"))
    if venue and "virtual" in venue.lower():
        return []

    url = f"{BASE_URL}{CITY_PATH}/products/{slug}"
    if "yoga" in slug.lower():
        event_type = "SocialEvent"
    elif "pizza" in slug.lower() or "cooking" in slug.lower():
        event_type = "FoodEvent"
    else:
        event_type = "SportsEvent"

    address, end_time_text = fetch_product_details(session, slug)
    price = clean(card.get("fromPricePaise")) or 0
    price_rupees = price // 100

    base = {
        "name": title,
        "@type": event_type,
        "url": url,
        "@context": "https://schema.org",
        "keywords": ["SISTERSINSWEAT"],
        "audience": {"@type": "Audience", "AudienceType": "women"},
        "eventAttendanceMode": "OfflineEventAttendanceMode",
        "eventStatus": "EventScheduled",
        "inLanguage": "en",
        "organizer": {
            "@type": "Organization",
            "name": "Sisters In Sweat",
            "url": "https://sistersinsweat.com",
        },
        "description": f"See more details at {url}",
        "isAccessibleForFree": price_rupees == 0,
        "offers": [
            {"@type": "Offer", "price": str(price_rupees), "priceCurrency": "INR"}
        ],
    }
    if event_type == "SportsEvent":
        base["keywords"].append("SISTERSINSWEAT/SPORTS")
        sport = guess_sport(card, slug)
        if sport:
            base["sport"] = sport
    else:
        base["keywords"].append("SISTERSINSWEAT/SESSION")

    image = clean(card.get("bannerImageUrl"))
    if image:
        base["image"] = BASE_URL + image
    if venue and address:
        base["location"] = {"name": venue, "address": address, "type": "Place"}

    now = datetime.datetime.now(IST)
    horizon = now + FUTURE_WINDOW
    occurrences = clean(card.get("occurrenceDates")) or []
    events = []
    for occurrence in occurrences:
        start = datetime.datetime.fromisoformat(occurrence).astimezone(IST)
        if start < now or start > horizon:
            continue
        event = dict(base)
        event["startDate"] = start.isoformat()
        if end_time_text and len(occurrences) == 1:
            end = parse_end_time(start, end_time_text)
            if end:
                event["endDate"] = end.isoformat()
        events.append(event)
    return events


if __name__ == "__main__":
    session = requests.Session()
    events = []
    for card in fetch_cards(session):
        events.extend(make_events(session, card))
    with open("out/sis.json", "w") as f:
        json.dump(events, f, indent=2)
