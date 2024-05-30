import json
from common import firebase
from requests_cache import CachedSession
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, timezone

URL = "https://firestore.googleapis.com/v1/projects/tonight-is/databases/(default)/documents/parties"
def fetch_parties():
    session = CachedSession(
            "event-fetcher-cache",
            expire_after=timedelta(days=1),
            stale_if_error=True,
            use_cache_dir=True,
            cache_control=False,
        )
    return json.loads(session.get(URL).content)

with open('fixtures/tonight-is-parties.json', 'r') as f:
    data = firebase.Firebase.parse_firebase_struct(fetch_parties()['documents'])
    with open("out/tonight.json", "w") as file:
        json.dump(data, file, indent=2)
