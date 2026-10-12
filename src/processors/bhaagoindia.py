import html
import logging
from .base import Processor
import datefinder
from ..common.tz import IST


def parse(value):
    if not isinstance(value, str):
        return None
    text = value.replace(".", "").replace(",", "").lower().replace("sept", "sep")
    return next(datefinder.find_dates(text), None)


class BhaagoIndia(Processor):
    URL_REGEX = r"^https?://(www\.)?bhaagoindia\.com/"

    @staticmethod
    def process(url, event):
        for x in ["startDate", "endDate"]:
            if x not in event:
                continue
            date = parse(event[x])
            if date is None:
                logging.warning("BhaagoIndia found no date in %s %r for %s", x, event[x], url)
                continue
            event[x] = date.replace(tzinfo=IST).isoformat()
        return event
