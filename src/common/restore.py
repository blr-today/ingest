import glob
import json
import os
import shutil
import sys

from src.common import bookmyshow
from src.sources import district

USAGE = "Usage: python -m src.common.restore bms|district <folder>"


def stamp(path, key):
    try:
        with open(path, encoding="utf-8") as f:
            return float(json.load(f)[key])
    except (OSError, ValueError, KeyError, TypeError):
        return -1


def take(path, folder, key, mine=()):
    """Copies path into folder when it is newer than every file in mine"""
    target = os.path.join(folder, os.path.basename(path))
    theirs = stamp(path, key)
    if theirs < 0 or any(stamp(p, key) >= theirs for p in mine or [target]):
        return False
    os.makedirs(folder, exist_ok=True)
    shutil.copy2(path, target + ".tmp")
    os.replace(target + ".tmp", target)
    for other in mine:
        if other != target:
            os.unlink(other)
    return True


def bms(source):
    folder = bookmyshow.cache_dir()
    taken = take(os.path.join(source, "listing.json"), folder, "listed")
    pages = 0
    for path in glob.glob(os.path.join(source, "????-??-??-*.json")):
        code = os.path.basename(path)[11:-5]
        mine = glob.glob(os.path.join(folder, f"????-??-??-{code}.json"))
        pages += take(path, folder, "fetched", mine)
    return f"listing {'taken' if taken else 'kept'}, {pages} newer pages"


def pages(source):
    path = os.path.join(source, os.path.basename(district.cache_path()))
    taken = take(path, os.path.dirname(district.cache_path()), "listed")
    return f"pages {'taken' if taken else 'kept'}"


if __name__ == "__main__":
    merge = {"bms": bms, "district": pages}
    if len(sys.argv) != 3 or sys.argv[1] not in merge:
        sys.exit(USAGE)
    if os.path.isdir(sys.argv[2]):
        print(sys.argv[1], sys.argv[2], merge[sys.argv[1]](sys.argv[2]))
