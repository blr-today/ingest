from .base import DROP, Processor
from .cost import flatten, price

LIMIT = 15000


class Costly(Processor):
    # Runs early so dropped events skip the slower processors
    PRIORITY = 1

    @staticmethod
    def process(url, event):
        prices = (
            price(offer)
            for offer in flatten(event.get("offers"))
            if (offer.get("priceCurrency") or "INR") == "INR"
        )
        prices = [p for p in prices if p is not None]
        if prices and min(prices) > LIMIT:
            print(f"[COSTLY] {url} dropped, cheapest ticket is {min(prices):.0f}")
            return DROP
        return None
