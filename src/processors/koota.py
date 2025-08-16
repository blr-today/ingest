import html
from .base import Processor

class Koota(Processor):
    URL_REGEX = r"^https?://(www\.)?courtyardkoota\.com/"
    for x in ["startDate", "endDate"]:
        if x in event:
            # HACK: This is specific to Courtyard Koota
            # where dates are not in ISO format
            event[x] = event[x].replace("+5.5:00", "+05:30")
            time = year = None
            if "T" in event[x]:
                date, time = event[x].split("T")
                year, month, day = date.split("-")
            else:
                yy = event[x].split("-")
                if len(yy) == 3:
                    year, month, day = yy
            if year:
                month = month.zfill(2)
                day = day.zfill(2)
                event[x] = f"{year}-{month}-{day}"
                if time:
                    event[x] = f"{event[x]}T{time}"

    return event
