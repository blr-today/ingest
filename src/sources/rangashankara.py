from bs4 import BeautifulSoup
from common.session import get_cached_session
from common.tz import IST
import json
import logging
import os
import re
from datetime import datetime, time, timedelta

PAGE_API = "https://rangashankara.org/wp-json/wp/v2/pages/1885?_fields=content"
PAGE_URL = "https://rangashankara.org/book-tickets-2/"
MONTH_RE = re.compile(r"^([A-Z][a-z]+) (\d{4})$")
DAY_RE = re.compile(r"^[A-Za-z]{3}\.?,?\s*(\d{1,2})(?:st|nd|rd|th)?\s*\|\s*(.+)$", re.S)
TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap]m)?", re.I)
AGE_RE = re.compile(r"(\d+)\s*\+\s*years?", re.I)
LANGUAGES = {
    "kan": "kn", "kannada": "kn", "eng": "en", "english": "en",
    "hin": "hi", "hindi": "hi", "mal": "ml", "malayalam": "ml",
    "bangla": "bn", "bengali": "bn", "tamil": "ta", "telugu": "te",
    "marathi": "mr", "urdu": "ur", "konkani": "kok", "tulu": "tcy",
}

LOCATION = {
    "@type": "Place",
    "name": "Ranga Shankara",
    "address": {
        "@type": "PostalAddress",
        "streetAddress": "36/2, 8th Cross Road, 2nd Phase, J P Nagar",
        "addressLocality": "Bengaluru",
        "addressRegion": "Karnataka",
        "postalCode": "560078",
        "addressCountry": "IN",
    },
    "geo": {
        "@type": "GeoCoordinates",
        "latitude": "12.91155",
        "longitude": "77.58707",
    },
}

logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()))
session = get_cached_session()


def parse_times(text):
    # A bare time like "7:30" is assumed to be evening
    times = []
    for hour, minute, meridian in TIME_RE.findall(text):
        hour = int(hour)
        if hour < 12 and meridian.lower() != "am":
            hour += 12
        times.append(time(hour, int(minute or 0)))
    return times


def parse_card(texts, link, month, year):
    clean = [re.sub(r"\s+", " ", t).strip() for t in texts]
    day = DAY_RE.match(texts[0].replace("\xa0", " ").strip())
    if not day or len(clean) < 3:
        return []
    schedule = re.split(r"\d+\s*min", day.group(2))[0]
    name = next((c for c in reversed(clean) if c and c != "Book Tickets!"), "")
    clock = parse_times(schedule)
    if not name or not clock:
        logging.warning("Dropping malformed card %s", clean)
        return []

    info = re.sub(r"\s+", " ", day.group(2).split("min.", 1)[-1]).strip(" |.")
    age = AGE_RE.search(info)
    spoken = [
        LANGUAGES.get(l.lower(), l.title())
        for l in re.split(r"\s*(?:,|&|/|\band\b)\s*", AGE_RE.sub("", info).strip(" .|"))
        if l
    ]
    details = " | ".join(c for c in clean[1:-2] if c)
    duration = re.search(r"(\d+)\s*min", clean[0])
    events = []
    for start_time in clock:
        start = datetime(year, month, int(day.group(1))).replace(
            hour=start_time.hour, minute=start_time.minute, tzinfo=IST
        )
        event = {
            "@type": "TheaterEvent",
            "name": name,
            "url": f"{PAGE_URL}#{start:%Y%m%d-%H%M}",
            "startDate": start.isoformat(),
            "location": LOCATION,
        }
        if details:
            event["description"] = details
        if spoken:
            event["inLanguage"] = spoken
        if age:
            event["typicalAgeRange"] = f"{age[1]}+"
        if duration:
            event["endDate"] = (start + timedelta(minutes=int(duration[1]))).isoformat()
        if link:
            event["sameAs"] = link
        events.append(event)
    return events


def get_events():
    response = session.get(PAGE_API)
    response.raise_for_status()
    soup = BeautifulSoup(response.json()["content"]["rendered"], "html.parser")

    events, month, year = [], None, None
    for heading in soup.select("h2.elementor-heading-title"):
        header = MONTH_RE.match(heading.get_text(" ", strip=True))
        if header:
            month = datetime.strptime(header[1], "%B").month
            year = int(header[2])
        elif month and DAY_RE.match(heading.get_text("\n").replace("\xa0", " ").strip()):
            card = heading.find_parent(class_="e-child")
            texts = [h.get_text("\n") for h in card.select("h2.elementor-heading-title")]
            anchor = card.select_one("a[href*=bookmyshow]")
            events.extend(
                parse_card(texts, anchor["href"] if anchor else None, month, year)
            )

    today = datetime.now(IST).date()
    return [e for e in events if datetime.fromisoformat(e["startDate"]).date() >= today]


if __name__ == "__main__":
    events = get_events()
    with open("out/rangashankara.json", "w") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f"[RANGASHANKARA] {len(events)} events")
