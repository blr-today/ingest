import re

from .base import Processor

TAGS = ["FREE", "₹", "₹₹", "₹₹₹"]


def flatten(offers):
    if isinstance(offers, list):
        for offer in offers:
            yield from flatten(offer)
    elif isinstance(offers, dict):
        # District lists unticketed events as zero-priced AggregateOffers
        if "offers" in offers or offers.get("offerCount") in (0, "0"):
            yield from flatten(offers.get("offers"))
        else:
            yield offers


def price(offer):
    value = offer.get("price", offer.get("lowPrice"))
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    if value.strip().lower() == "free":
        return 0.0
    match = re.search(r"\d+(\.\d+)?", value.replace(",", ""))
    return float(match.group()) if match else None


def tag(amount):
    if amount == 0:
        return "FREE"
    if amount < 500:
        return "₹"
    return "₹₹" if amount < 2000 else "₹₹₹"


def as_keywords(keywords):
    if isinstance(keywords, dict):
        keywords = keywords.get("content", "")
    if isinstance(keywords, str):
        return [k.strip() for k in keywords.split(",") if k.strip()]
    return keywords if isinstance(keywords, list) else []


class Cost(Processor):
    PRIORITY = 900

    @staticmethod
    def process(url, event):
        prices = []
        for offer in flatten(event.get("offers")):
            amount = price(offer)
            currency = offer.get("priceCurrency") or "INR"
            if amount is None or (amount > 0 and currency != "INR"):
                continue
            name = str(offer.get("name") or "").lower()
            if amount == 0 and "couple" in name:
                continue
            prices.append(amount)
        if prices:
            label = tag(min(prices))
        elif event.get("isAccessibleForFree") in (True, "true", "True"):
            label = "FREE"
        else:
            return event
        keywords = [k for k in as_keywords(event.get("keywords")) if k not in TAGS]
        event["keywords"] = keywords + [label]
        return event
