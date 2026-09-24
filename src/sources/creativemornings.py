from common.jsonld import JsonLdExtractor
from bs4 import BeautifulSoup
from datetime import datetime, timezone
import json
import os
import re
import subprocess

BASE_URL = "https://creativemornings.com"
TALK_LINK = re.compile(r"^/talks/[a-z0-9-]+$")


def render(url, wait_for):
    # AWS WAF serves a JS challenge to plain HTTP clients, so render with lightpanda
    result = subprocess.run(
        [
            os.environ.get("LIGHTPANDA", "lightpanda"),
            "fetch",
            "--log-level",
            "err",
            "--wait-script",
            f"document.querySelector('{wait_for}')",
            "--wait-ms",
            "30000",
            "--dump",
            "html",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=dict(os.environ, LIGHTPANDA_DISABLE_TELEMETRY="true"),
    )
    return result.stdout


def scrape_cm(location):
    html = render(f"{BASE_URL}/cities/{location}", 'a[href^="/talks/"]')
    soup = BeautifulSoup(html, "html.parser")
    links = {
        a["href"]
        for a in soup.select("a[href^='/talks/']")
        if TALK_LINK.match(a["href"]) and a["href"] != "/talks/upcoming"
    }

    events = []
    for link in sorted(links):
        url = BASE_URL + link
        data = JsonLdExtractor().extract(
            render(url, 'script[type="application/ld+json"]')
        )
        event = next((d for d in data if d.get("@type") == "Event"), None)
        if not event:
            print(f"[CREATIVEMORNINGS] No event in {url}")
            continue
        start = datetime.fromisoformat(event["startDate"].replace("Z", "+00:00"))
        if start < datetime.now(timezone.utc):
            print(f"[CREATIVEMORNINGS] Event in past: {url}")
            continue
        event["url"] = url
        events.append(event)
    return events


if __name__ == "__main__":
    events = scrape_cm("BLR")
    with open("out/creativemornings.json", "w") as f:
        json.dump(events, f, indent=2)
    print(f"[CREATIVEMORNINGS] {len(events)} events")
