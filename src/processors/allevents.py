import html
import logging
from .base import Processor
from datetime import datetime, timezone
from ..common.tz import IST


class AllEvents(Processor):
    URL_REGEX = r"^https?://(www\.)?allevents\.in/"

    @staticmethod
    def process(url, event):
        if "@type" in event:
            event["@type"] = "Event"
        for x in ["startDate", "endDate"]:
            value = event.get(x)
            if not isinstance(value, str) or not value.endswith("+.000+0"):
                continue
            try:
                naive = datetime.fromisoformat(value[0:19])
            except ValueError:
                logging.warning("AllEvents could not read %s %r for %s", x, value, url)
                continue
            event[x] = naive.replace(tzinfo=timezone.utc).astimezone(IST).isoformat()
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
