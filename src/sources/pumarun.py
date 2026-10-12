from .eventbrite import events as _events


def events():
    return _events("pumarun")
