import os
import json
import http.client
import urllib.parse
import pickle
import cleanurl

CACHE_FILE = ".cache.pkl"
KNOWN_SHORTENERS = [
    "bit.ly",
    # 'hi.switchy.io' switchy doesn't use a 3xx, so this breaks
]


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "rb") as f:
            return pickle.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(cache, f)


def expand_link(link):
    cache = load_cache()
    if link in cache:
        return cache[link]

    parsed_url = urllib.parse.urlparse(link)
    path = parsed_url.path
    connection = http.client.HTTPSConnection(parsed_url.netloc)
    connection.request("HEAD", path)
    expanded_url = connection.getresponse().getheader("Location")
    if expanded_url:
        cache[link] = expanded_url
        save_cache(cache)
        return expanded_url
    else:
        return link


def fetch_venn():
    events = []
    event_ids = set()
    for d in ["today", "tomorrow", "later"]:
        url = f"https://api.venn.buzz/user/social_experiences.json?filter={d}"
        connection = http.client.HTTPSConnection("api.venn.buzz")
        connection.request("GET", url)
        response = connection.getresponse()
        data = json.loads(response.read().decode("utf-8"))
        for event in data["data"]["events"]:
            while True:
                # get hostname from the URL
                hostname = urllib.parse.urlparse(event["shortened_link"]).hostname
                # if the hostname is a known shortener, expand the link
                if hostname in KNOWN_SHORTENERS:
                    event["shortened_link"] = expand_link(event["shortened_link"])
                else:
                    break
            event["url"] = cleanurl.cleanurl(
                event["shortened_link"], respect_semantics=True
            ).url

            for k in ["curation", "shortened_link", "test_event", "experience_id"]:
                if k in event:
                    del event[k]
            if event["id"] not in event_ids:
                events.append(event)
                event_ids.add(event["id"])
    return sorted(events, key=lambda x: x["id"])


# Write to venn.json
if __name__ == "__main__":
    with open("out/venn.json", "w") as f:
        json.dump(fetch_venn(), f, indent=2)
