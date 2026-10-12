from src.jsonnet import transform


def events():
    with open("out/tpcc.jsonnet") as f:
        return transform("tpcc", f.read())
