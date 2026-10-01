import re
from .base import Processor

LANGUAGE_MAP = {
    "English": "en",
    "Hindi": "hi",
    "Kannada": "kn",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml",
    "Marathi": "mr",
    "Bengali": "bn",
    "Gujarati": "gu",
    "Punjabi": "pa",
    "Odia": "or",
    "Assamese": "as",
    "Urdu": "ur",
    "Nepali": "ne",
    "Sindhi": "sd",
}

SCRIPTS = {
    "kn": r"\u0c80-\u0cff",
    "hi": r"\u0900-\u097f",
    "bn": r"\u0980-\u09ff",
    "pa": r"\u0a00-\u0a7f",
    "gu": r"\u0a80-\u0aff",
    "or": r"\u0b00-\u0b7f",
    "ta": r"\u0b80-\u0bff",
    "te": r"\u0c00-\u0c7f",
    "ml": r"\u0d00-\u0d7f",
}


class ScriptLanguage(Processor):
    # A title written wholly in one Indian script names its language
    @staticmethod
    def process(url, event):
        name = event.get("name")
        if not isinstance(name, str) or re.search(r"[A-Za-z]", name):
            return event
        if event.get("inLanguage") not in (None, "", "en"):
            return event
        for code, chars in SCRIPTS.items():
            if re.search(f"[{chars}]", name):
                event["inLanguage"] = code
                break
        return event
