from src.common.remote import events_from_urls


def events():
    with open("out/allevents.txt") as f:
        return events_from_urls(f.read().splitlines())
