# Returned by a processor to delete the event instead of updating it
DROP = "DROP"


class Processor:
    URL_REGEX = None

    @staticmethod
    def process(url, event):
        return None
