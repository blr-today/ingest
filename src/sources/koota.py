from src.common.remote import events_from_urls


def events():
    with open("out/koota.txt") as f:
        return events_from_urls(f.read().splitlines())
