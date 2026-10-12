import logging

from src.common import bookmyshow

from .base import Processor

_seen = {}


def bms_link(event):
    links = event.get("sameAs") or []
    for link in [links] if isinstance(links, str) else links:
        if isinstance(link, str) and bookmyshow.EVENT_PAGE.match(link):
            return link


class BookMyShow(Processor):
    # Fill gaps from the linked BMS page, before cost and type processors run
    @staticmethod
    def process(url, event):
        link = bms_link(event)
        if not link:
            return event
        if link not in _seen:
            try:
                _seen[link] = bookmyshow.details(link)
            except Exception as e:
                logging.warning("BookMyShow lookup failed for %s: %s", link, e)
                _seen[link] = {}
        for key, value in _seen[link].items():
            if not event.get(key):
                event[key] = value
        return event
