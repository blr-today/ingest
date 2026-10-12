import html
from .base import Processor
from datetime import datetime
from ..common.tz import IST


class AllEvents(Processor):
    URL_REGEX = r"^https?://(www\.)?allevents\.in/"

    @staticmethod
    def process(url, event):
        for x in ["startDate", "endDate"]:
            if event[x].endswith("+.000+0"):
                event[x] = (
                    datetime.fromisoformat(event[x][0:19]).astimezone(IST).isoformat()
                )
        place = event.get("location")
        geo = place.get("geo") if isinstance(place, dict) else None
        # Unknown venues sit on Google's centre of Bangalore, which is wrong
        try:
            lat, lng = float(geo["latitude"]), float(geo["longitude"])
            if abs(lat - 12.9716) < 1e-4 and abs(lng - 77.5946) < 1e-4:
                del place["geo"]
        except KeyError, TypeError, ValueError:
            pass
        return event
