from .meetup import events as _events


def events():
    return _events("hsrmeetups")
