import datetime
import json
import os
import sys
import tempfile
import time

import curl_cffi
import requests
from src.common.remote import page_event
from src.common.tz import IST

URL = "https://www.district.in/gw/web/get_discovery_results"
LAT, LNG = 12.9716, 77.5946
CITIES = ("Bengaluru", "Bangalore")
HEADERS = {
    "content-type": "application/json",
    "x-guest-token": "1212",
    "x-app-type": "ed_web",
    "x-available-tabs": "events",
    "x-user-lat": str(LAT),
    "x-user-lng": str(LNG),
}
LOCATION = {"user_lat": LAT, "user_lng": LNG, "gps_lat": LAT, "gps_lng": LNG}
DEBUG_HEADERS = ("content-type", "server", "server-timing", "x-cache", "akamai-grn")
# District blocks cloud IPs, so a self-hosted job crawls and builds read its saved pages
DAY = 24 * 3600
STALE = 2 * DAY
MAX_AGE = 7 * DAY
MAX_FETCHES = 600


def log(*args):
    print("[DISTRICT]", *args, file=sys.stderr)


def describe(client, r):
    headers = {k: r.headers.get(k) for k in DEBUG_HEADERS if r.headers.get(k)}
    log(client, r.status_code, len(r.content), "bytes", headers)


def post(session, body):
    r = session.post(URL, headers=HEADERS, json=body, timeout=30)
    describe("requests", r)
    try:
        return r.json()
    except ValueError:
        log("non-JSON body:", r.text[:500])
    r = curl_cffi.post(
        URL, headers=HEADERS, json=body, timeout=30, impersonate="chrome"
    )
    describe("curl_cffi", r)
    try:
        return r.json()
    except ValueError:
        log("non-JSON body:", r.text[:500])
        raise


def pages(session, limit=300):
    body = {"location": LOCATION, "layout_type": "events_home_v2"}
    for page in range(limit):
        response = post(session, body)["EDSResponse"]
        log("page", page, "has_more", response.get("has_more"))
        yield response
        if not response.get("has_more"):
            break
        body = {
            "location": LOCATION,
            "layout_type": "events_home_v2",
            "request_type": "load_more",
            "postback_params": response["postback_params"],
        }


def event_data(node):
    if isinstance(node, dict):
        if "EventData" in node:
            yield node["EventData"]
        for value in node.values():
            yield from event_data(value)
    elif isinstance(node, list):
        for value in node:
            yield from event_data(value)


def crawling():
    return bool(os.getenv("DISTRICT_CRAWL"))


def cache_path():
    folder = os.path.expanduser(os.getenv("DISTRICT_CACHE", "~/.cache/district"))
    return os.path.join(folder, "pages.json")


def today():
    return datetime.datetime.now(IST).date().isoformat()


def load():
    try:
        with open(cache_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data.get("pages"), dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def save(pages):
    folder = os.path.dirname(cache_path())
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"listed": time.time(), "pages": pages}, f, ensure_ascii=False)
        os.replace(tmp, cache_path())
    except BaseException:
        os.unlink(tmp)
        raise


def day(event):
    return str(event.get("startDate") or "")[:10]


def due(page):
    try:
        days = (datetime.date.fromisoformat(day(page["event"])) - datetime.date.fromisoformat(today())).days
    except ValueError:
        days = 30
    age = DAY // 2 if days <= 1 else 2 * DAY if days <= 7 else 4 * DAY
    return time.time() - page["fetched"] > age


def upcoming(event):
    end = str(event.get("endDate") or event.get("startDate") or "")[:10]
    return not end or end >= today()


def slugs():
    found = set()
    for response in pages(requests.Session()):
        for event in event_data(response.get("rails")):
            if event.get("city") in CITIES and event.get("event_slug"):
                found.add(event["event_slug"])
    log(len(found), "Bengaluru events")
    return found


def crawl():
    listed, old = sorted(slugs()), load().get("pages", {})
    new = [s for s in listed if s not in old]
    stale = sorted((s for s in listed if s in old and due(old[s])), key=lambda s: old[s]["fetched"])
    fetch = (new + stale)[: int(os.getenv("DISTRICT_MAX_FETCHES", MAX_FETCHES))]
    found = {s: old[s] for s in listed if s in old}
    session = requests.Session()
    for slug in fetch:
        event = page_event(session, f"https://district.in/{slug}/event")
        if event:
            found[slug] = {"fetched": time.time(), "event": event}
    log(len(fetch), "pages fetched,", len(set(new) - set(fetch)), "new and", len(set(stale) - set(fetch)), "stale left")
    # A partial discovery should not replace a fuller copy
    if len(found) < len(old) / 2:
        raise RuntimeError(f"Only {len(found)} pages, the saved copy has {len(old)}")
    save(found)
    return found


def saved():
    data = load()
    age = time.time() - float(data.get("listed", 0))
    if not 0 <= age <= MAX_AGE:
        raise RuntimeError(f"District pages at {cache_path()} are {age / 3600:.0f}h old")
    if age > STALE:
        log(f"using pages from {age / 3600:.0f}h ago")
    return data["pages"]


def events():
    found = [p["event"] for p in (crawl() if crawling() else saved()).values()]
    found = [e for e in found if upcoming(e)]
    log(len(found), "upcoming events")
    return found
