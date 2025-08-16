from .base import Processor

"""
HighApe events have a free entry offer with price 0
for all events, which is not shown on the website
so we drop that.        
"""
class HighApe(Processor):
    URL_REGEX = r"^https?://(www\.)?highape\.com/"

    @staticmethod
    def process(url, event):
        try:
            if (event["offers"][-1]["price"] == "0"
                and event["offers"][-1]["name"] == "Entry"
            ):
                del event["offers"][-1]
        except (KeyError, IndexError):
            pass
        return event
