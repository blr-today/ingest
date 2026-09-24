"""
Sumukha Gallery Exhibition Scraper

Fetches exhibition data from sumukha.com and converts to Schema.org Event format.

Process:
1. Fetch the /exhibitions page and read the "exhibitions" array out of the
   Next.js RSC payload (the site is a client-rendered app now, so there are
   no plain <a href> links to individual exhibitions in the markup any more)
2. Coarsely filter to exhibitions that could still be ongoing/upcoming
3. For each candidate, fetch the exhibition page and parse the header div,
   locating the date paragraph by pattern rather than position, since the
   header can carry an optional subtitle paragraph before/after the dates
4. Filter to ongoing/future exhibitions using the exact end date
"""

from bs4 import BeautifulSoup
from common.session import get_cached_session
from common.tz import IST
import json
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

BASE_URL = "https://sumukha.com"
EXHIBITIONS_URL = f"{BASE_URL}/exhibitions"
IMAGE_BASE = "https://smg-dev.imatix.in/api/smgdata/ent/exhibition/og"
DATE_RE = re.compile(r"^[A-Za-z]+ \d{1,2},\s*\d{4}")

LOCATION = {
    "@type": "Place",
    "name": "Gallery Sumukha",
    "address": {
        "@type": "PostalAddress",
        "streetAddress": "24/10, BTS Depot Road, Wilson Garden",
        "addressLocality": "Bengaluru",
        "addressRegion": "Karnataka",
        "postalCode": "560027",
        "addressCountry": "IN",
    },
}

session = get_cached_session()


def parse_date_range(date_str):
    """Parse date range like 'January 15, 2026 to February 26, 2026'."""
    if " to " in date_str:
        start_str, end_str = [d.strip() for d in date_str.split(" to ")]
    else:
        start_str = end_str = date_str.strip()

    try:
        start_date = datetime.strptime(start_str, "%B %d, %Y").replace(tzinfo=IST)
        end_date = datetime.strptime(end_str, "%B %d, %Y").replace(tzinfo=IST)
        return start_date, end_date
    except ValueError:
        return None, None


def extract_rsc_payload(html):
    """The exhibitions list is hydrated from the Next.js RSC stream, not markup."""
    soup = BeautifulSoup(html, "html.parser")
    rsc = ""
    for script in soup.find_all("script"):
        m = re.match(r"self\.__next_f\.push\(\[1,(\".*\")\]\)", script.string or "", re.S)
        if m:
            rsc += json.loads(m.group(1))
    return rsc


def fetch_exhibition_candidates():
    """Return exhibition ids whose listed end date hasn't clearly passed yet.

    The listing's start/end dates carry an odd time-of-day offset, so this
    is only used to avoid fetching every exhibition since 1996; the real
    filtering happens against the exact dates on each exhibition page.
    """
    response = session.get(EXHIBITIONS_URL)
    rsc = extract_rsc_payload(response.text)
    start = rsc.index('"exhibitions":') + len('"exhibitions":')
    exhibitions, _ = json.JSONDecoder().raw_decode(rsc, start)

    cutoff = datetime.now(IST).date() - timedelta(days=2)
    candidates = []
    for ex in exhibitions:
        end_str = ex.get("end_date", "").lstrip("$D").replace("Z", "+00:00")
        try:
            end_date = datetime.fromisoformat(end_str).date()
        except ValueError:
            continue
        if end_date >= cutoff:
            candidates.append(ex)
    return candidates


def parse_exhibition_page(url, main_image):
    """Parse exhibition details from an exhibition page."""
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    header = soup.select_one("div.text-center.mb-16")
    if not header:
        return None

    title_elem = header.select_one("h1")
    if not title_elem:
        return None
    title = title_elem.text.strip()

    # Match the date paragraph by pattern; an optional subtitle shifts positions
    p_tags = header.select("p.text-base.text-gray-600")
    date_p = next((p for p in p_tags if DATE_RE.match(p.text.strip())), None)
    if date_p is None:
        return None

    start_date, end_date = parse_date_range(date_p.text.strip())
    if not start_date or not end_date:
        return None

    today = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    if end_date < today:
        return None

    subtitle = next(
        (p.text.strip() for p in p_tags if p is not date_p and p.text.strip() != "Gallery Sumukha"),
        "",
    )

    prose = soup.select_one(".prose")
    description = prose.get_text(separator="\n").strip() if prose else ""
    if subtitle:
        description = f"{subtitle}\n\n{description}" if description else subtitle

    image = urljoin(f"{IMAGE_BASE}/", main_image) if main_image else ""

    return {
        "@type": "ExhibitionEvent",
        "name": title,
        "startDate": start_date.replace(hour=0, minute=0, second=0).isoformat(),
        "endDate": end_date.replace(hour=23, minute=59, second=59).isoformat(),
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "url": url,
        "image": image,
        "description": description,
        "location": LOCATION,
        "isAccessibleForFree": True,
    }


def main():
    candidates = fetch_exhibition_candidates()
    events = []

    for ex in candidates:
        url = f"{BASE_URL}/exhibitions/{ex['id']}"
        event = parse_exhibition_page(url, ex.get("main_image"))
        if event:
            events.append(event)

    events.sort(key=lambda x: x["startDate"])

    with open("out/sumukha.json", "w") as f:
        json.dump(events, f, indent=2)

    print(f"[SUMUKHA] {len(events)} events")


if __name__ == "__main__":
    main()
