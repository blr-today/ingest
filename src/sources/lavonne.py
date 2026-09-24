import json
import re
from datetime import datetime
from bs4 import BeautifulSoup
from common.tz import IST
from common.session import get_cached_session

URL = "https://lavonne.in/courses/weekend-classes"


def parse_time_range(time_str, base_date):
    """Parse time range like '10:00 am to 1:00 pm' and attach to base_date"""
    start_time, end_time = time_str.split(" to ")
    start = datetime.strptime(f"{base_date} {start_time}", "%Y-%m-%d %I:%M %p")
    end = datetime.strptime(f"{base_date} {end_time}", "%Y-%m-%d %I:%M %p")
    return start.replace(tzinfo=IST), end.replace(tzinfo=IST)


def fetch_classes(html):
    """The classes list lives in the Next.js RSC payload, not in plain markup"""
    soup = BeautifulSoup(html, "html.parser")
    rsc = ""
    for script in soup.find_all("script"):
        m = re.match(r"self\.__next_f\.push\(\[1,(\".*\")\]\)", script.string or "", re.S)
        if m:
            rsc += json.loads(m.group(1))
    start = rsc.index('"classes":') + len('"classes":')
    classes, _ = json.JSONDecoder().raw_decode(rsc, start)
    return [{k: (None if v == "$undefined" else v) for k, v in c.items()} for c in classes]


def make_event(c):
    start_time, end_time = parse_time_range(c["time"], c["date"])
    description = c["description"]
    if c.get("whatYoullLearn"):
        description += "\n" + c["whatYoullLearn"]

    offer = {
        "@type": "Offer",
        "price": str(c["feeAmount"]),
        "priceCurrency": "INR",
        "availability": "https://schema.org/SoldOut"
        if c.get("soldOut")
        else "https://schema.org/InStock",
    }
    if c.get("remainingSeats"):
        offer["remainingAttendeeCapacity"] = int(c["remainingSeats"])

    return {
        "@type": "EducationEvent",
        "name": c["title"],
        "description": description,
        "url": f"{URL}#class-{c['id']}",
        "image": c.get("image"),
        "startDate": start_time.isoformat(),
        "endDate": end_time.isoformat(),
        "offers": offer,
        "location": {
            "@type": "Place",
            "name": "Lavonne Academy",
            "address": {
                "@type": "PostalAddress",
                "streetAddress": "263, 3rd Cross Rd, Stage 2, Domlur",
                "addressLocality": "Bangalore",
                "addressRegion": "Karnataka",
                "addressCountry": "IN",
            },
        },
    }


if __name__ == "__main__":
    session = get_cached_session()
    response = session.get(URL)
    classes = fetch_classes(response.text)
    events = [make_event(c) for c in classes if c.get("location") == "Bangalore"]

    with open("out/lavonne.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
        print(f"[LAVONNE] {len(events)} events")
