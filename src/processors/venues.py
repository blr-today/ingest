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


# Listings append the city or the area to the venue's own name
SUFFIX = re.compile(r"\s*(\|.*|[:,]\s*(bengaluru|bangalore)\W*)$", re.IGNORECASE)
CITY = re.compile(
    r"\s*[,:|-]\s*(bengaluru|bangalore)(\s*,\s*karnataka)?(\s*,\s*india)?\W*$",
    re.IGNORECASE,
)


def lookup(name):
    name = normalize(SUFFIX.sub("", name))
    for venue in venues():
        for alias in venue["match"]:
            # One-word names like Courtyard must match the whole venue name
            if name == alias or (" " in alias and f" {alias} " in f" {name} "):
                return venue
    return None


def near(venue, lat, lng, metres):
    north = (venue["latitude"] - lat) * 110_600
    east = (venue["longitude"] - lng) * 109_000
    return north * north + east * east <= metres * metres


def nearest(lat, lng, metres=30):
    return next((v for v in venues() if near(v, lat, lng, metres)), None)


def pin(place, venue):
    place["geo"] = {
        "@type": "GeoCoordinates",
        "latitude": venue["latitude"],
        "longitude": venue["longitude"],
    }


class Venues(Processor):
    # Runs after AllEvents drops its placeholder coordinates
    @staticmethod
    def process(url, event):
        place = event.get("location")
        if not isinstance(place, dict):
            return event
        geo = place.get("geo")
        name = str(place.get("name") or "").strip()
        # The city belongs in the address, not the place name
        if CITY.search(name):
            name = place["name"] = CITY.sub("", name)
        if not geo:
            venue = lookup(name)
            if venue:
                pin(place, venue)
            return event
        try:
            lat, lng = float(geo["latitude"]), float(geo["longitude"])
        except KeyError, TypeError, ValueError:
            return event
        # Hosts like Urbanaut's leave the venue unnamed but pinned
        if not name:
            venue = nearest(lat, lng)
            if venue:
                place["name"] = venue["name"]
                pin(place, venue)
            return event
        # Listings pin one venue metres apart, which splits it on the map
        venue = lookup(name)
        if venue and near(venue, lat, lng, 100):
            pin(place, venue)
        return event
