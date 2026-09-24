from .session import get_cached_session
from bs4 import BeautifulSoup
import urllib.parse
import json


class EB:
    def __init__(self, organizer_id: str):
        self.url = f"https://www.eventbrite.com/o/{organizer_id}"
        self.session = get_cached_session()

    def fetch_links(self):
        """Extracts unique Eventbrite event links from the organizer page.

        The events bucket is hydrated client-side now, so the listing
        is read from the __NEXT_DATA__ payload instead of the markup.

        Returns:
            list: A list of unique Eventbrite event links without query parameters.
        """
        soup = BeautifulSoup(self.session.get(self.url).content, "html.parser")

        next_data = soup.find("script", id="__NEXT_DATA__")
        if not next_data or not next_data.string:
            return []

        data = json.loads(next_data.string)
        events = data.get("props", {}).get("pageProps", {}).get("upcomingEvents") or []

        # Extract base URLs, remove query parameters
        unique_links = set()
        for event in events:
            url = urllib.parse.urlparse(event["url"])
            base_url = f"https://www.eventbrite.com{url.path}"
            unique_links.add(base_url)

        return list(unique_links)
