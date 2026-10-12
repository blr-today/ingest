import yaml
from src.common import eventbrite
from src.common.remote import events_from_urls


def urls(key):
    with open("in/known-hosts.yml") as f:
        organizer_id = yaml.safe_load(f)["eventbrite"][key]["id"]
    return eventbrite.EB(organizer_id).fetch_links()


def events(key):
    return events_from_urls(sorted(urls(key)))
