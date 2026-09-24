import json
import re
from datetime import datetime, timedelta, time
import dateutil.parser
from common.tz import IST
from common.session import get_cached_session

SITE_URL = "https://mainmission.in"
FIRESTORE_URL = (
    "https://firestore.googleapis.com/v1/projects/fmc-43566484-d5f6d/"
    "databases/(default)/documents/events"
)
ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
TIME_TOKEN_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([APap][Mm])?")
OUT_OF_CITY = (
    "goa", "mysore", "mysuru", "coorg", "chennai", "mumbai", "delhi",
    "pune", "hyderabad", "kochi", "chikmagalur", "gokarna", "hampi",
)


def decode_value(v):
    if "stringValue" in v:
        return v["stringValue"]
    if "integerValue" in v:
        return int(v["integerValue"])
    if "doubleValue" in v:
        return v["doubleValue"]
    if "booleanValue" in v:
        return v["booleanValue"]
    if "nullValue" in v:
        return None
    if "arrayValue" in v:
        return [decode_value(x) for x in v["arrayValue"].get("values", [])]
    if "mapValue" in v:
        return {k: decode_value(x) for k, x in v["mapValue"].get("fields", {}).items()}
    return None


def fetch_events(session):
    docs = []
    page_token = None
    # public REST listing of the Firestore "events" collection, no auth needed
    while True:
        params = {"pageSize": 300}
        if page_token:
            params["pageToken"] = page_token
        data = session.get(FIRESTORE_URL, params=params, timeout=30).json()
        for doc in data.get("documents", []):
            fields = {k: decode_value(v) for k, v in doc["fields"].items()}
            fields["_id"] = doc["name"].rsplit("/", 1)[-1]
            docs.append(fields)
        page_token = data.get("nextPageToken")
        if not page_token:
            break
    return docs


def parse_event_date(date_str):
    if not date_str:
        return None
    date_str = date_str.strip()
    m = ISO_DATE_RE.match(date_str)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
    try:
        return dateutil.parser.parse(date_str, fuzzy=True, default=datetime.now()).date()
    except (ValueError, OverflowError):
        return None


def parse_time_range(time_str):
    if not time_str:
        return None, None
    cleaned = re.sub(r"\bonwards\b", "", time_str, flags=re.IGNORECASE)
    parts = [
        p.strip()
        for p in re.split(r"\s*-\s*|\s+to\s+", cleaned, flags=re.IGNORECASE)
        if p.strip()
    ]
    parsed = []
    last_ampm = None
    for part in reversed(parts):
        m = TIME_TOKEN_RE.search(part)
        if not m:
            continue
        hour, minute, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3)
        ampm = (ampm or last_ampm or "").lower()
        last_ampm = ampm or last_ampm
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23:
            parsed.append(time(hour, minute))
    parsed.reverse()
    if len(parsed) >= 2:
        return parsed[0], parsed[-1]
    if len(parsed) == 1:
        return parsed[0], None
    return None, None


def build_datetimes(date_str, time_str):
    d = parse_event_date(date_str)
    if not d:
        return None, None
    start_t, end_t = parse_time_range(time_str)
    start_dt = datetime.combine(d, start_t or time(9, 0), tzinfo=IST)
    if end_t:
        end_dt = datetime.combine(d, end_t, tzinfo=IST)
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)
    else:
        # community events with no listed end time are assumed 2 hours long
        end_dt = start_dt + timedelta(hours=2)
    return start_dt, end_dt


def get_image(e):
    iu = e.get("imageUrl")
    if isinstance(iu, dict):
        return iu.get("highRes") or iu.get("original") or iu.get("lowRes")
    if isinstance(iu, str) and iu:
        return iu
    for item in e.get("imageUrls") or []:
        if isinstance(item, dict):
            img = item.get("highRes") or item.get("original") or item.get("lowRes")
            if img:
                return img
        elif isinstance(item, str) and item:
            return item
    return None


def parse_price(price_str):
    if not price_str:
        return 0.0
    price_str = price_str.strip()
    if not price_str or price_str.lower() in ("free", "0", "rsvp pass"):
        return 0.0
    m = re.search(r"[\d,]+(?:\.\d+)?", price_str)
    if m:
        return float(m.group(0).replace(",", ""))
    return 0.0


def is_bengaluru(location_str):
    if not location_str or not location_str.strip():
        return False
    haystack = location_str.lower()
    return not any(re.search(rf"\b{city}\b", haystack) for city in OUT_OF_CITY)


def make_event(e, now):
    title = re.sub(r"\s+", " ", (e.get("title") or "")).strip()
    location_str = re.sub(r"\s+", " ", (e.get("location") or "")).strip()
    if e.get("hidden") or e.get("draft") or not title or not is_bengaluru(location_str):
        return None

    start_dt, end_dt = build_datetimes(e.get("date"), e.get("time"))
    if not start_dt or start_dt < now:
        return None

    url = f"{SITE_URL}/#/events/{e['_id']}"
    price = parse_price(e.get("price"))
    haystack = location_str.lower()
    address = location_str if "beng" in haystack or "bangalore" in haystack else f"{location_str}, Bengaluru, Karnataka, India"

    event = {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": title,
        "startDate": start_dt.isoformat(),
        "endDate": end_dt.isoformat(),
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
        "url": url,
        "location": {
            "@type": "Place",
            "name": location_str,
            "address": address,
        },
        "isAccessibleForFree": price == 0,
        "offers": [
            {
                "@type": "Offer",
                "price": str(price if price % 1 else int(price)),
                "priceCurrency": "INR",
                "availability": (
                    "https://schema.org/SoldOut"
                    if e.get("soldOut")
                    else "https://schema.org/InStock"
                ),
                "url": e.get("link") or url,
            }
        ],
        "organizer": {"@type": "Organization", "name": "Main Mission", "url": SITE_URL},
    }
    description = (e.get("description") or "").strip()
    if description:
        event["description"] = description
    image = get_image(e)
    if image:
        event["image"] = image
    tags = [t for t in (e.get("tags") or []) if isinstance(t, str)]
    if tags:
        event["keywords"] = tags
    return event


if __name__ == "__main__":
    session = get_cached_session()
    docs = fetch_events(session)
    now = datetime.now(IST)
    events = [ev for ev in (make_event(e, now) for e in docs) if ev]
    events.sort(key=lambda ev: ev["startDate"])
    with open("out/mainmission.json", "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2, ensure_ascii=False)
    print(f"[MAINMISSION] {len(events)} events")
