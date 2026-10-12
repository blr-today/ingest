import html
import logging
from .base import Processor
from .cost import as_keywords
from urllib.parse import urlparse
import datefinder
from datetime import datetime, timedelta
from ..common.tz import IST
import re

# Emoji, arrows, dingbats and object-replacement marks that decorate titles
SYMBOL = "[\U0001f000-\U0001faff\u2190-\u21ff\u2300-\u23ff\u25a0-\u27bf\u2b00-\u2bff\ufe0e\ufe0f\u200d\u20e3\ufffc]"
EDGES = re.compile(rf"^(?:{SYMBOL}|\s)+|(?:{SYMBOL}|\s)+$")


def get_domain(url):
    subdomain = urlparse(url).netloc
    if subdomain.startswith("www."):
        return subdomain[4:]
    return subdomain


class SchemaFixer(Processor):
    URL_REGEX = None

    @staticmethod
    def process(url, event):
        # Insider events often include &apos; &quot; etc.
        if isinstance(event.get("name"), str):
            event["name"] = html.unescape(event["name"])
            event["name"] = EDGES.sub("", event["name"]) or event["name"]
        elif "name" in event:
            logging.warning("SchemaFixer found a name that is not text for %s", url)

        # force https here
        event["@context"] = "https://schema.org"

        # set a url if not already set
        if "url" not in event:
            event["url"] = url

        # fix format to ISO and timezone to IST
        for x in ["startDate", "endDate"]:
            if x in event:
                try:
                    date = datetime.fromisoformat(event[x])
                    date = date if date.tzinfo else date.replace(tzinfo=IST)
                    event[x] = date.astimezone(IST).isoformat()
                except Exception as e:
                    print(f"[IMP] Error parsing {x} for {event['url']}: {e}")
                    pass

        if "endDate" not in event and "startDate" in event:
            try:
                event["endDate"] = (
                    datetime.fromisoformat(event["startDate"]) + timedelta(hours=2)
                ).isoformat()
            except TypeError, ValueError:
                pass

        try:
            if isinstance(event["organizer"], list) and len(event["organizer"]) == 1:
                event["organizer"] = event["organizer"][0]
        except KeyError:
            pass
        if event.get("LOCATION"):
            event["location"] = event.pop("LOCATION")

        # post-build.sql can only append tags to a keywords array
        keywords = (k.strip() for k in as_keywords(event.get("keywords")) if isinstance(k, str))
        event["keywords"] = list(dict.fromkeys(k for k in keywords if k))

        return event
