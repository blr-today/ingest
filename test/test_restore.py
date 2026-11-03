import json
import os

from src.common import restore


def write(path, **data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_bms_takes_newer_pages_and_listing(monkeypatch, tmp_path):
    mine, theirs = tmp_path / "mine", tmp_path / "theirs"
    monkeypatch.setenv("BMS_CACHE", str(mine))
    write(mine / "listing.json", listed=5)
    write(theirs / "listing.json", listed=3)
    write(mine / "2026-10-16-ET1.json", fetched=1)
    write(theirs / "2026-10-18-ET1.json", fetched=2)
    write(mine / "2026-10-16-ET2.json", fetched=2)
    write(theirs / "2026-10-16-ET2.json", fetched=1)
    write(theirs / "2026-10-20-ET3.json", fetched=1)
    assert restore.bms(str(theirs)) == "listing kept, 2 newer pages"
    assert sorted(os.listdir(mine)) == ["2026-10-16-ET2.json", "2026-10-18-ET1.json", "2026-10-20-ET3.json", "listing.json"]
    assert json.loads((mine / "listing.json").read_text())["listed"] == 5
    assert json.loads((mine / "2026-10-16-ET2.json").read_text())["fetched"] == 2


def test_district_takes_the_newer_copy(monkeypatch, tmp_path):
    mine, theirs = tmp_path / "mine", tmp_path / "theirs"
    monkeypatch.setenv("DISTRICT_CACHE", str(mine))
    write(theirs / "pages.json", listed=2, pages={})
    assert restore.pages(str(theirs)) == "pages taken"
    write(theirs / "pages.json", listed=1, pages={})
    assert restore.pages(str(theirs)) == "pages kept"
    assert json.loads((mine / "pages.json").read_text())["listed"] == 2
