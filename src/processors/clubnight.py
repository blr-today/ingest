from .base import DROP, Processor
from .cost import flatten, price


class ClubNight(Processor):
    URL_REGEX = r"^https?://(www\.)?district\.in/"

    # District files free venue promos (DJ nights, ladies nights) as music events
    @staticmethod
    def process(url, event):
        if event.get("@type") != "MusicEvent":
            return None
        prices = [price(offer) for offer in flatten(event.get("offers"))]
        if prices and all(p == 0 for p in prices):
            print(f"[CLUBNIGHT] {url} dropped, free venue promo")
            return DROP
        return None
