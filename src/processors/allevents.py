import html
from .base import Processor
from datetime import datetime


class AllEvents(Processor):
    URL_REGEX = r"^https?://(www\.)?allevents\.in/"

    @staticmethod
    def process(url, event):
        for x in ["startDate", "endDate"]:
            if event[x].endswith("+.000+0"):
                event[x] = (
                    datetime.fromisoformat(event[x][0:19]).astimezone(IST).isoformat()
                )
        return event
