import html
from .base import Processor
from urllib.parse import urlparse
import datefinder
from datetime import datetime, timedelta
from ..common.tz import IST
def get_domain(url):
    subdomain = urlparse(url).netloc
    if subdomain.startswith('www.'):
        return subdomain[4:]
    return subdomain

class SchemaFixer(Processor):
    PRIORITY = 0
    URL_REGEX = None

    @staticmethod
    def process(url, event):
        # Insider events often include &apos; &quot; etc.
        if "name" in event:
            event['name'] = html.unescape(event["name"])

        # force https here
        event["@context"] = "https://schema.org"

        # set a url if not already set
        if "url" not in event:
            event["url"] = url

        # fix format to ISO and timezone to IST
        for x in ["startDate", "endDate"]:
            if x in event:
                try:
                    event[x] = datetime.fromisoformat(event[x]).astimezone(IST).isoformat()
                except Exception as e:
                    print(f"[IMP] Error parsing {x} for {event['url']}: {e}")
                    pass

        if "endDate" not in event:
            event["endDate"] = (
                datetime.fromisoformat(event["startDate"]) + timedelta(hours=2)
            ).isoformat()

        
        try:
            if isinstance(event["organizer"], list) and len(event["organizer"]) == 1:
                event["organizer"] = event["organizer"][0]
        except KeyError:
            pass
        if event.get("LOCATION"):
            event["location"] = event.pop("LOCATION")


        return event
