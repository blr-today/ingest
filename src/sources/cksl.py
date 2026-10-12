import json

from src.common import icalendar
from src.jsonnet import transform


def events():
    return transform("cksl", json.dumps(icalendar.convert_ics_to_events("out/cksl.ics")))
