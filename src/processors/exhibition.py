from .base import Processor


class Exhibition(Processor):
    # Runs after SchemaFixer, so dates are already ISO in IST
    PRIORITY = 10

    @staticmethod
    def process(url, event):
        # Exhibitions span days; their opening hours are not start/end times
        if event.get("@type") != "ExhibitionEvent":
            return event
        for key in ("startDate", "endDate"):
            if isinstance(event.get(key), str):
                event[key] = event[key][:10]
        return event
