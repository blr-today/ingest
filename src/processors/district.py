from .base import Processor
from .languages import LANGUAGE_MAP


class District(Processor):
    URL_REGEX = r"^https?://(www\.)?(insider|district)\.in/"

    @staticmethod
    def process(url, event):
        # These are workarounds for broken schema published by Insider
        try:
            if "language" in event["inLanguage"]:
                event["inLanguage"]["name"] = event["inLanguage"]["language"]
                event["inLanguage"]["alternateName"] = LANGUAGE_MAP.get(
                    event["inLanguage"]["language"], "und"
                )
                del event["inLanguage"]["language"]
        except:
            pass

        try:
            if event["typicalAgeRange"]["@type"] == "Age-Range":
                event["typicalAgeRange"] = event["typicalAgeRange"]["language"]
        except:
            pass

        # insider reports keywords as a dict (incorrectly) so we ignore and rewrite
        # from meta tags
        if "keywords" in event:
            try:
                current_keywords = event["keywords"]
                if isinstance(current_keywords, str):
                    keywords = ",".join(set(current_keywords.split(",")))
                    event["keywords"] = keywords
            except:
                pass

        return event
