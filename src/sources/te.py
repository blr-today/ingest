from src.jsonnet import transform


def events():
    with open("out/te.jsonnet") as f:
        return transform("te", f.read())
