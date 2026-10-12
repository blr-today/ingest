import json
import re
import unicodedata
from functools import cache

from .base import Processor


def normalize(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"['’]", "", text.lower())
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


@cache
def venues():
    with open("patch/venues.json") as f:
        return json.load(f)


def lookup(name):
    name = normalize(name)
    for venue in venues():
        for alias in venue["match"]:
            # One-word names like Courtyard must match the whole venue name
            if name == alias or (" " in alias and f" {alias} " in f" {name} "):
                return venue
    return None


class Venues(Processor):
    # Runs after AllEvents drops its placeholder coordinates
    PRIORITY = 120

    @staticmethod
    def process(url, event):
        place = event.get("location")
        if not isinstance(place, dict) or place.get("geo"):
            return event
        venue = lookup(str(place.get("name") or ""))
        if venue:
            place["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": venue["latitude"],
                "longitude": venue["longitude"],
            }
        return event
