"""
Geo Processor

Checks if events are within Bangalore (50km radius) based on their geo coordinates.
Tags events outside this radius with NOTINBLR keyword.
"""

from math import radians, sin, cos, sqrt, atan2
from .base import Processor

# Bangalore center coordinates
BLR_LAT = 12.964989402811952
BLR_LNG = 77.58848208150272
MAX_DISTANCE_KM = 50


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points in kilometers."""
    R = 6371  # Earth's radius in kilometers

    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def extract_coords(event):
    """Extract latitude and longitude from event location."""
    location = event.get("location")
    if not location:
        return None, None

    # Handle location as dict
    if isinstance(location, dict):
        geo = location.get("geo")
        if geo and isinstance(geo, dict):
            lat = geo.get("latitude")
            lng = geo.get("longitude")
            if lat is not None and lng is not None:
                try:
                    return float(lat), float(lng)
                except (ValueError, TypeError):
                    pass

    return None, None


class GeoProcessor(Processor):
    PRIORITY = 90  # Run before most other processors

    @staticmethod
    def process(url, event):
        lat, lng = extract_coords(event)

        if lat is None or lng is None:
            return event

        # Drop invalid geo coordinates (lat or lng is zero)
        if lat == 0 or lng == 0:
            location = event.get("location")
            if isinstance(location, dict) and "geo" in location:
                del location["geo"]
            return event

        distance = haversine_distance(lat, lng, BLR_LAT, BLR_LNG)

        if distance > MAX_DISTANCE_KM:
            keywords = event.get("keywords", [])
            if isinstance(keywords, dict):
                keywords = []
            if "NOTINBLR" not in keywords:
                keywords = keywords + ["NOTINBLR"]
                event["keywords"] = sorted(list(set(keywords)))

        return event
