IGNORED_EVENT_UIDS = []
from .base import Processor


class IgnoredEvents(Processor):
    URL_REGEX = None

    @staticmethod
    def process(url, event):
        if event.get("@id") in IGNORED_EVENT_UIDS:
            return None
