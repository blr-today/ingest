import html
from .base import Processor
import datefinder
from ..common.tz import IST


class BhaagoIndia(Processor):
    URL_REGEX = r"^https?://(www\.)?bhaagoindia\.com/"

    @staticmethod
    def process(url, event):
        for x in ["startDate", "endDate"]:
            startdate = event[x].replace(".", "").replace(",", "").lower()
            startdate = startdate.replace("sept", "sep")
            event[x] = (
                list(datefinder.find_dates(startdate))[0]
                .replace(tzinfo=IST)
                .isoformat()
            )
        return event
