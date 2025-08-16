from .session import get_cached_session
from bs4 import BeautifulSoup
import json


class Linktree:
    def __init__(self, slug):
        self.url = f"https://linktr.ee/{slug}"
        self.session = get_cached_session()

    def fetch_links(self):
        soup = BeautifulSoup(self.session.get(self.url).content, "html.parser")
        data = json.loads(soup.select_one("#__NEXT_DATA__").string)
        for link in data["props"]["pageProps"]["links"]:
            if link["type"] == "CLASSIC":
                yield {
                    "title": link["title"],
                    "url": link["url"],
                    "thumbnail": link["thumbnail"],
                }
