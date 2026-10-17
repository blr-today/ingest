import re

from .base import DROP, Processor
from .cost import flatten, price

STAG = re.compile(r"\bstags?\b", re.I)
LADIES = re.compile(r"\b(lad(y|ies)|female)\b", re.I)
COUPLE = re.compile(r"\bcouples?\b", re.I)
DJ = re.compile(r"\b(v?dj|club night|bollywood night)\b", re.I)


def reason(event):
    offers = list(flatten(event.get("offers")))
    names = [offer.get("name") or "" for offer in offers]
    if any(STAG.search(n) for n in names):
        return "stag entry"
    music = event.get("@type") == "MusicEvent"
    if (
        (music or event.get("@type") == "Event")
        and any(LADIES.search(n) for n in names)
        and any(COUPLE.search(n) for n in names)
    ):
        return "couple and ladies entry"
    if not music:
        return None
    prices = [price(offer) for offer in offers]
    if prices and all(p == 0 for p in prices):
        return "free venue promo"
    name = event.get("name") or ""
    if DJ.search(name) and "live music" not in name.lower():
        return "DJ night"
    return None


class ClubNight(Processor):
    URL_REGEX = r"^https?://(www\.)?district\.in/"

    # Clubs sell stag, couple and ladies entry; gigs and comedy do not
    @staticmethod
    def process(url, event):
        why = reason(event)
        if why:
            print(f"[CLUBNIGHT] {url} dropped, {why}")
            return DROP
        return None
