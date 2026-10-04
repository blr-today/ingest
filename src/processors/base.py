# Returned by a processor to delete the event instead of updating it
DROP = "DROP"


class Processor:
    PRIORITY = 100
    URL_REGEX = None

    @staticmethod
    def process(url, event):
        return None
