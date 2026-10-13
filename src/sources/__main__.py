import importlib
import json
import os
import sys
import tempfile
import traceback

USAGE = "Usage: python -m src.sources <name>, writes out/<name>.json"


def write(path, events):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def run(name):
    label = name.upper()
    try:
        events = importlib.import_module(f"src.sources.{name}").events()
        if not isinstance(events, list) or not all(isinstance(e, dict) for e in events):
            raise TypeError(f"events() returned {type(events).__name__}, not a list of dicts")
        write(os.path.join("out", f"{name}.json"), events)
    except Exception as e:
        print(f"[{label}] FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1
    print(f"[{label}] {len(events)} events")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(USAGE)
    sys.exit(run(sys.argv[1]))
