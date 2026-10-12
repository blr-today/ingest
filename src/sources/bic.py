from src.common import icalendar


def events():
    return icalendar.convert_ics_to_events("out/bic.ics")
