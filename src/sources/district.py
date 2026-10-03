import requests

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


def pages(session, limit=300):
    body = {"location": LOCATION, "layout_type": "events_home_v2"}
    for _ in range(limit):
        data = session.post(URL, headers=HEADERS, json=body, timeout=30).json()
        response = data["EDSResponse"]
        yield response
        if not response.get("has_more"):
            break
        body = {
            "location": LOCATION,
            "layout_type": "events_home_v2",
            "request_type": "load_more",
            "postback_params": response["postback_params"],
        }


def events(node):
    if isinstance(node, dict):
        if "EventData" in node:
            yield node["EventData"]
        for value in node.values():
            yield from events(value)
    elif isinstance(node, list):
        for value in node:
            yield from events(value)


if __name__ == "__main__":
    slugs = set()
    for response in pages(requests.Session()):
        for event in events(response.get("rails")):
            if event.get("city") in CITIES and event.get("event_slug"):
                slugs.add(event["event_slug"])
    for slug in sorted(slugs):
        print(f"https://district.in/{slug}/event")
