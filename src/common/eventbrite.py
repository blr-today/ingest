from common.session import get_cached_session
from bs4 import BeautifulSoup
import urllib.parse
import json


class EB:
    def __init__(self, organizer_id: str):
        self.url = f"https://www.eventbrite.com/o/{organizer_id}"
        self.session = get_cached_session()

    def fetch_links(self):
        """Extracts unique Eventbrite event links from raw HTML.

        Returns:
            list: A list of unique Eventbrite event links without query parameters.
        """
        soup = BeautifulSoup(self.session.get(self.url).content, "html.parser")

        links = soup.select('div[data-testid="organizer-profile__future-events"] a[href^="https://www.eventbrite.com/e/"]')

        # Extract base URLs, remove query parameters
        unique_links = set()
        for link in links:
            url = urllib.parse.urlparse(link['href'])
            base_url = f"https://www.eventbrite.com{url.path}"
            unique_links.add(base_url)

        return list(unique_links)
