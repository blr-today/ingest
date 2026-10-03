import json
import re
import sys
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from common import USER_AGENT_HEADERS
from common.jsonld import JsonLdExtractor
from common.remote import find_event
from common.session import get_cached_session

SITE_URL = "https://underline.center"
SKIP = ("underline.center", "instagram.com", "whatsapp.com", "facebook.com", "wa.me")


def post_text(cooked):
    soup = BeautifulSoup(cooked, "html.parser")
    for el in soup.select(".discourse-post-event, .lightbox-wrapper, img"):
        el.decompose()
    text = soup.get_text("\n")
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


def event_links(session, event, cooked):
    # Ticket links sit in the url, the location or anywhere in the post
    text = " ".join([event.get("url") or "", event.get("location") or ""])
    hrefs = [a["href"] for a in BeautifulSoup(cooked, "html.parser").select("a[href]")]
    links = []
    for url in re.findall(r"https?://\S+", text) + hrefs:
        if re.match(r"https?://(link|at)\.underline\.center/", url):
            url = session.get(url, timeout=30).url
        host = urlparse(url).netloc
        if url.startswith("http") and not any(host.endswith(d) for d in SKIP):
            links.append(url)
    return list(dict.fromkeys(links))


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
        event["links"] = event_links(session, event, cooked)
        for url in event["links"]:
            if "district.in/" not in url or event.get("offers"):
                continue
            try:
                event["offers"] = ticket_offers(session, url, event["starts_at"])
            except Exception as e:
                print(f"[UNDERLINE] Could not read {url}: {e}")
    with open(path, "w") as f:
        json.dump(data, f)


if __name__ == "__main__":
    main(sys.argv[1])
