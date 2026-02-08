"""
Sumukha Gallery Exhibition Scraper

Fetches exhibition data from sumukha.com and converts to Schema.org Event format.

Process:
1. Fetch homepage to find all /exhibitions/{id} links
2. For each exhibition page, parse details from the header div
3. Filter to ongoing/future exhibitions only
4. Extract description from .prose section
"""

from bs4 import BeautifulSoup
from common.session import get_cached_session
import json
import re
from urllib.parse import urljoin
from datetime import datetime

BASE_URL = "https://sumukha.com"
session = get_cached_session()


def parse_date_range(date_str):
    """Parse date range like 'January 15, 2026 to February 26, 2026'."""
    # Handle "to" separator
    if " to " in date_str:
        start_str, end_str = [d.strip() for d in date_str.split(" to ")]
    else:
        start_str = end_str = date_str.strip()

    # Parse dates
    try:
        start_date = datetime.strptime(start_str, "%B %d, %Y")
        end_date = datetime.strptime(end_str, "%B %d, %Y")
        return start_date, end_date
    except ValueError:
        return None, None


def fetch_exhibition_links():
    """Fetch homepage and extract all /exhibitions/{id} links."""
    response = session.get(BASE_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/exhibitions/" in href:
            full_url = urljoin(BASE_URL, href)
            # Normalize URL (remove trailing slash, query params)
            full_url = full_url.split("?")[0].rstrip("/")
            if re.match(r"https://sumukha\.com/exhibitions/\d+", full_url):
                links.add(full_url)

    return sorted(links)


def parse_exhibition_page(url):
    """Parse exhibition details from exhibition page."""
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # Find the header div with exhibition details
    header = soup.select_one("div.text-center.mb-16")
    if not header:
        return None

    # Extract title
    title_elem = header.select_one("h1")
    if not title_elem:
        return None
    title = title_elem.text.strip()

    # Extract date range and location from p tags
    p_tags = header.select("p.text-base.text-gray-600")
    if len(p_tags) < 2:
        return None

    date_str = p_tags[0].text.strip()
    location = p_tags[1].text.strip()

    # Parse dates
    start_date, end_date = parse_date_range(date_str)
    if not start_date or not end_date:
        return None

    # Filter: only ongoing or future exhibitions
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if end_date < today:
        return None

    # Extract description from .prose
    prose = soup.select_one(".prose")
    description = prose.get_text(separator="\n").strip() if prose else ""

    # Extract image
    img = soup.select_one("img")
    image = urljoin(BASE_URL, img["src"]) if img and img.get("src") else ""

    return {
        "name": title,
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "url": url,
        "image": image,
        "description": description
    }


def main():
    links = fetch_exhibition_links()
    events = []

    for url in links:
        event = parse_exhibition_page(url)
        if event:
            events.append(event)

    # Sort by start date
    events.sort(key=lambda x: x["startDate"])

    with open("out/sumukha.json", "w") as f:
        json.dump(events, f, indent=2)

    print(f"[SUMUKHA] {len(events)} events")


if __name__ == "__main__":
    main()
