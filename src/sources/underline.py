import json
import re
import sys
from datetime import datetime

from bs4 import BeautifulSoup

from common import USER_AGENT_HEADERS
from common.jsonld import JsonLdExtractor
from common.remote import find_event
from common.session import get_cached_session

SITE_URL = "https://underline.center"


def post_text(cooked):
    soup = BeautifulSoup(cooked, "html.parser")
    for el in soup.select(".discourse-post-event, .lightbox-wrapper, img"):
        el.decompose()
    text = soup.get_text("\n")
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def ticket_offers(session, url, starts_at):
    # District pages carry prices, but old links point at past shows
    r = session.get(url, headers=USER_AGENT_HEADERS, timeout=30)
    data = JsonLdExtractor().extract(r.text)
    graphs = [find_event(x["@graph"]) for x in data if x.get("@graph")]
    event = next(filter(None, graphs), None) or find_event(data) or {}
    try:
        start = datetime.fromisoformat(event["startDate"])
        if start == datetime.fromisoformat(starts_at):
            return event.get("offers")
    except (KeyError, TypeError, ValueError):
        pass
    return None


# The events feed leaves descriptions empty, so read each event's post
def main(path):
    with open(path) as f:
        data = json.load(f)
    session = get_cached_session()
    for event in data["events"]:
        if event.get("is_expired"):
            continue
        r = session.get(f"{SITE_URL}/posts/{event['post']['id']}.json", timeout=30)
        if r.status_code != 200:
            continue
        post = r.json()
        cooked = post.get("cooked", "")
        event["description"] = post_text(cooked)
        img = BeautifulSoup(cooked, "html.parser").select_one(".lightbox, img")
        if not event.get("image_upload") and img:
            event["image_upload"] = {"url": img.get("href") or img.get("src")}
        event["post"]["topic"]["slug"] = post.get("topic_slug")
        links = [event.get("url") or "", (event.get("location") or "").split(" ")[0]]
        url = next((u for u in links if u.startswith("http")), "")
        if "district.in/" in url:
            try:
                offers = ticket_offers(session, url, event["starts_at"])
            except Exception as e:
                print(f"[UNDERLINE] Could not read {url}: {e}")
                offers = None
            if offers:
                event["offers"] = offers
    with open(path, "w") as f:
        json.dump(data, f)


if __name__ == "__main__":
    main(sys.argv[1])
