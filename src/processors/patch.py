from .base import Processor
from .languages import LANGUAGE_MAP
from functools import cache
from urllib.parse import urlparse
import os
import json

def get_root_domain_easy(url):
    domain = urlparse(url).netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

@cache
def get_patch(url):
    domain = get_root_domain_easy(url)
    patch_file = os.path.join("patch", f"{domain}.json")
    if os.path.exists(patch_file):
        with open(patch_file, "r") as file:
            return json.load(file)
    return None

# TODO: Patch PUMARUN and TOWNSCRIPT events correctly somehow
class Patch(Processor):
    URL_REGEX = None

    @staticmethod
    def process(url, event):
        patch = get_patch(url)
        if not patch:
            return event
        patch = patch.copy()
        if 'keywords' in patch:
            # Combine keywords and remove duplicates
            combined_keywords = event.get("keywords", []) + patch["keywords"]
            patch["keywords"] = sorted(list(set(combined_keywords)))
            if 'keywords' in event:
                del event['keywords']
        patch.update(event)
        return patch
