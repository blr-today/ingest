import json
import re
import sys

from bs4 import BeautifulSoup

from common.session import get_cached_session

SITE_URL = "https://underline.center"


def post_text(cooked):
    soup = BeautifulSoup(cooked, "html.parser")
    for el in soup.select(".discourse-post-event, .lightbox-wrapper, img"):
        el.decompose()
    text = soup.get_text("\n")
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


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
    with open(path, "w") as f:
        json.dump(data, f)


if __name__ == "__main__":
    main(sys.argv[1])
