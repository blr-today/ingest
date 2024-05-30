from requests_cache import CachedSession
from datetime import timedelta
from bs4 import BeautifulSoup
import json

class Linktree():
    def __init__(self, slug):
        self.url = f"https://linktr.ee/{slug}"
        self.session = CachedSession(
            "event-fetcher-cache",
            expire_after=timedelta(days=1),
            stale_if_error=True,
            use_cache_dir=True,
            cache_control=False,
        )

    def fetch_links(self):
        soup = BeautifulSoup(self.session.get(self.url).content, "html.parser")
        data = json.loads(soup.select_one("#__NEXT_DATA__").string)
        for link in data['props']['pageProps']['links']:
            if link['type'] == 'CLASSIC':
                yield {
                    "title": link['title'],
                    "url": link['url'],
                    "thumbnail": link['thumbnail']
                }
