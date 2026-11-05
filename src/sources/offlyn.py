import datetime
import logging
from concurrent.futures import ThreadPoolExecutor

from ..common.remote import page_event
from ..common.session import get_cached_session
from ..common.tz import IST

API = "https://api.offlyn.club/api/utils/experiences"
PAGE = "https://offlyn.life/e/"
LIMIT = 32
log = logging.getLogger(__name__)


def experiences(session):
    page, found = 1, []
    while True:
        r = session.get(API, params={"page": page, "limit": LIMIT, "city": "Bengaluru"}, timeout=60)
        r.raise_for_status()
        batch = r.json()["experiences"]
        found += batch
        if not batch or len(found) >= r.json()["total"]:
            return found
        page += 1


def ist(value):
    return datetime.datetime.fromisoformat(value).astimezone(IST).isoformat()


def place(location):
    address = (location.get("description") or "").strip()
    if address in ("", "Unknown"):
        address = "Bengaluru"
    venue = {"@type": "Place", "name": address.split(",")[0].strip(), "address": address}
    if location.get("locationStatus") == "hidden":
        venue["name"] = address
    point = (location.get("coordinates") or {}).get("coordinates")
    if point and len(point) == 2:
        venue["geo"] = {"@type": "GeoCoordinates", "latitude": point[1], "longitude": point[0]}
    return venue


def make_event(item):
    url = PAGE + (item.get("customShortId") or item["shortId"])
    schedule = item["schedule"]
    return {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": item["name"].strip(),
        "url": url,
        "startDate": ist(schedule["startDate"]),
        "endDate": ist(schedule.get("endDate") or schedule["startDate"]),
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": place(item.get("location") or {}),
        "organizer": {"@type": "Organization", "name": item["hostName"].strip()},
        "image": item.get("coverImage"),
        "keywords": item.get("tags") or [],
        "offers": {"@type": "Offer", "price": item.get("price", 0), "priceCurrency": "INR", "url": url},
    }


def enrich(session, event):
    page = page_event(session, event["url"], timeout=90)
    if not page:
        log.warning("[OFFLYN] No page details for %s", event["url"])
        return event
    if page.get("description"):
        event["description"] = page["description"].strip()
    if page.get("offers"):
        event["offers"] = page["offers"]
    return event


def upcoming(item, now):
    schedule = item.get("schedule") or {}
    end = schedule.get("endDate") or schedule.get("startDate")
    return bool(end) and datetime.datetime.fromisoformat(end) > now


def events():
    session = get_cached_session()
    now = datetime.datetime.now(IST)
    # The city filter also returns trips out of town, which GeoProcessor tags NOTINBLR
    items = [i for i in experiences(session) if i.get("name") and upcoming(i, now)]
    with ThreadPoolExecutor(8) as pool:
        return list(pool.map(lambda i: enrich(session, make_event(i)), items))
