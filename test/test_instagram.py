import json
from contextlib import nullcontext
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from src.common.tz import IST
from src.sources import instagram

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=IST)
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 32


def record(code, account="af_bangalore", caption="", posted="2026-10-14T10:00:00.000Z", **kw):
    return {
        "url": f"https://www.instagram.com/p/{code}",
        "shortcode": code,
        "pk": f"pk-{code}",
        "user_posted": account,
        "description": caption,
        "date_posted": posted,
        "photos": [f"https://cdn.example/{code}/1.jpg", f"https://cdn.example/{code}/2.jpg"],
        "location": None,
        "discovery_input": {"url": f"https://www.instagram.com/{account}/"},
    } | kw


class FakeResponse:
    def __init__(self, data=None, status_code=200, content=b""):
        self.data, self.status_code, self.content = data, status_code, content
        self.ok, self.text = status_code < 400, json.dumps(data)

    def json(self):
        return self.data

    def raise_for_status(self):
        if not self.ok:
            raise instagram.requests.HTTPError(str(self.status_code))


class FakeBrightData:
    def __init__(self, records, statuses=("running", "ready")):
        self.records, self.statuses = records, list(statuses)
        self.inputs, self.params = None, []

    def post(self, url, params, headers, json, timeout):
        assert params["dataset_id"] == instagram.DATASET
        self.params.append(params)
        self.inputs = json["input"]
        return FakeResponse({"snapshot_id": f"sd_{len(self.params)}"})

    def get(self, url, headers=None, params=None, timeout=None):
        if "/progress/" in url:
            return FakeResponse({"status": self.statuses.pop(0)})
        return FakeResponse(self.records)


class FakeJev:
    """Answers the text round with `text`, and each image round with `image`."""

    def __init__(self, text, image=None):
        self.text, self.image, self.calls = text, image, []

    def system_one(self, state, questions, **options):
        self.calls.append((state, options))
        nouls, choices = self.image if "poster" in state else self.text
        return SimpleNamespace(
            nouls={k: SimpleNamespace(noul=v) for k, v in nouls.items()},
            choices={k: SimpleNamespace(choice=c, confidence=0.9) for k, c in choices.items()},
        )


class FakeImages:
    def __init__(self, content=JPEG):
        self.content, self.urls = content, []

    def get(self, url, timeout=None):
        self.urls.append(url)
        return FakeResponse(content=self.content)


@pytest.fixture
def db(tmp_path):
    return instagram.connect(tmp_path / "cache.sqlite")


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(instagram.time, "sleep", lambda s: None)


def post(code="ABC", caption="Jazz Night\nSat 18 Oct, 7 PM"):
    return instagram.to_post(record(code, caption=caption), "af_bangalore")


DATED = ({"event": 0.9}, {"name": "Jazz Night", "month": "10", "day": "18", "start_hour": "19"})
UNDATED = ({"event": 0.6}, {"month": "none", "day": "none"})


def test_known_hosts_include_af_bangalore():
    assert "af_bangalore" in instagram.accounts()


def test_request_reads_a_window_and_skips_known_posts(db):
    first = instagram.request(db, "af_bangalore", NOW.date())
    assert first["start_date"] == "09-01-2026" and first["end_date"] == "10-17-2026"
    assert first["post_type"] == "post" and first["posts_to_not_include"] == []
    instagram.save(db, [record("ABC")], NOW)
    db.execute("INSERT INTO accounts VALUES ('af_bangalore', '2026-10-15T12:00:00+05:30')")
    later = instagram.request(db, "af_bangalore", NOW.date())
    assert later["start_date"] == "10-13-2026"
    assert later["posts_to_not_include"] == ["pk-ABC"]


def test_collect_caches_posts_and_accounts(db):
    api = FakeBrightData([record("ABC"), {"error_code": "dead_page", "input": {"url": "https://www.instagram.com/gone/"}}])
    instagram.collect(db, api, "key", ["af_bangalore", "gone"], NOW)
    assert [i["url"] for i in api.inputs] == ["https://www.instagram.com/af_bangalore/", "https://www.instagram.com/gone/"]
    assert db.execute("SELECT shortcode, account FROM posts").fetchall() == [("ABC", "af_bangalore")]
    assert {a for (a,) in db.execute("SELECT account FROM accounts")} == {"af_bangalore", "gone"}
    assert db.execute("SELECT * FROM snapshots").fetchall() == []
    assert instagram.due(db, ["af_bangalore"], NOW + timedelta(hours=1)) == []
    assert instagram.due(db, ["af_bangalore"], NOW + timedelta(days=1)) == ["af_bangalore"]


def test_rate_limited_accounts_are_asked_again(db):
    api = FakeBrightData([{"error_code": "bucket_rate_limit", "input": {"url": "https://www.instagram.com/af_bangalore/"}}])
    instagram.collect(db, api, "key", ["af_bangalore"], NOW)
    assert instagram.due(db, ["af_bangalore"], NOW) == ["af_bangalore"]


def test_unfinished_snapshot_is_resumed_next_run(db, monkeypatch):
    monkeypatch.setattr(instagram, "WAIT", -1)
    instagram.collect(db, FakeBrightData([], statuses=["running"]), "key", ["af_bangalore"], NOW)
    assert instagram.due(db, ["af_bangalore"], NOW) == []
    api = FakeBrightData([record("ABC")], statuses=["ready"])
    instagram.collect(db, api, "key", ["af_bangalore"], NOW)
    assert api.inputs is None
    assert db.execute("SELECT count(*) FROM posts").fetchone() == (1,)


def test_lines_drop_emoji_tags_and_link_in_bio():
    caption = "🎷 Jazz Night 🎷\n#jazz #bangalore\nLink in bio\n@someone\nSat 18 Oct"
    assert instagram.lines(caption) == ["Jazz Night"]


def test_lines_drop_dates_and_calls_to_action():
    caption = "Saturday, 17 October\n17 Oct 2026 12 PM\nDetails\nVisit BookMyShow for more details\nSunday Chatpata Breakfast\nMarch of the Penguins"
    assert instagram.lines(caption) == ["Sunday Chatpata Breakfast", "March of the Penguins"]


def test_text_answer_is_enough_without_images():
    jev, images = FakeJev(DATED), FakeImages()
    result = instagram.judge(jev, images, post())
    assert result["images"] == 0 and images.urls == []
    assert jev.calls[0][0] == {"account": "@af_bangalore", "posted_on": "Wednesday, 14 October 2026", "caption": "Jazz Night\nSat 18 Oct, 7 PM"}


def test_images_are_read_one_by_one_until_dated():
    jev, images = FakeJev(UNDATED, DATED), FakeImages()
    result = instagram.judge(jev, images, post())
    assert result["images"] == 1 and images.urls == ["https://cdn.example/ABC/1.jpg"]
    state, options = jev.calls[1]
    ref = state["poster"]
    assert options["extra_headers"] == instagram.IMAGES
    assert options["extra_body"]["assets"][ref]["format"] == "jpg"


def test_images_stop_at_the_limit():
    jev, images = FakeJev(UNDATED, UNDATED), FakeImages()
    assert instagram.judge(jev, images, post())["images"] == 2
    assert len(jev.calls) == 3


def test_non_image_downloads_are_skipped():
    jev = FakeJev(UNDATED, DATED)
    assert instagram.judge(jev, FakeImages(content=b"<html>"), post())["images"] == 0


def test_to_event_builds_a_dated_event():
    result = {"nouls": DATED[0], "picks": {k: [v, 0.9] for k, v in DATED[1].items()}}
    event = instagram.to_event(post(), result, NOW)
    assert event["name"] == "Jazz Night"
    assert event["url"] == "https://www.instagram.com/p/ABC/"
    assert event["startDate"] == "2026-10-18T19:00:00+05:30"
    assert event["organizer"]["url"] == "https://www.instagram.com/af_bangalore/"


def test_to_event_needs_an_event_and_a_date():
    picks = {"month": ["10", 0.9], "day": ["18", 0.9]}
    assert instagram.to_event(post(), {"nouls": {"event": 0.2}, "picks": picks}, NOW) is None
    assert instagram.to_event(post(), {"nouls": {"event": 0.9}, "picks": {}}, NOW) is None
    day_only = instagram.to_event(post(), {"nouls": {"event": 0.9}, "picks": picks}, NOW)
    assert day_only["startDate"] == "2026-10-18" and day_only["name"] == "Jazz Night"


def test_linked_elsewhere_reads_other_sources(tmp_path):
    (tmp_path / "puttingscene.json").write_text(json.dumps([{"sameAs": "https://www.instagram.com/p/DUVqs5OEnwS/?img_index=1"}]))
    (tmp_path / "instagram.json").write_text(json.dumps([{"url": "https://www.instagram.com/p/OWN/"}]))
    assert instagram.linked_elsewhere(str(tmp_path / "*.json")) == {"DUVqs5OEnwS"}


def test_events_merge_reminders_and_skip_linked_posts(db, monkeypatch, tmp_path):
    instagram.save(db, [
        record("NEW", posted="2026-10-15T10:00:00.000Z"),
        record("OLD", posted="2026-10-10T10:00:00.000Z"),
        record("LINKED"),
        record("PAST"),
    ], NOW)
    picks = {k: [v, 0.9] for k, v in DATED[1].items()}
    past = picks | {"month": ["10", 0.9], "day": ["1", 0.9], "year": ["2026", 0.9]}
    for code, p in [("NEW", picks), ("OLD", picks), ("LINKED", picks), ("PAST", past)]:
        db.execute("INSERT INTO answers VALUES (?, ?, ?)", (code, instagram.VERSION, json.dumps({"nouls": DATED[0], "picks": p})))
    monkeypatch.setattr(instagram, "connect", lambda: db)
    monkeypatch.setattr(instagram, "datetime", SimpleNamespace(now=lambda tz: NOW, combine=datetime.combine, fromisoformat=datetime.fromisoformat))
    monkeypatch.setattr(instagram, "linked_elsewhere", lambda: {"LINKED"})
    monkeypatch.setattr(instagram, "listings", lambda: {})
    monkeypatch.delenv("BRIGHT_DATA_API_KEY", raising=False)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    events = instagram.events()
    assert [e["url"] for e in events] == ["https://www.instagram.com/p/NEW/"]
    assert events[0]["sameAs"] == ["https://www.instagram.com/p/OLD/"]
    listing = {"name": "Jazz Night Live", "url": "https://venue.in/jazz", "startDate": "2026-10-18T19:30:00+05:30"}
    monkeypatch.setattr(instagram, "matches", lambda db, pairs, by_day: {"NEW": listing})
    merged = instagram.events()[0]
    assert merged["startDate"] == listing["startDate"]
    assert merged["sameAs"] == ["https://venue.in/jazz", "https://www.instagram.com/p/OLD/"]


LISTINGS = {"2026-10-18": [
    {"name": "Open Mic", "url": "https://other.in/mic", "startDate": "2026-10-18T19:00:00+05:30"},
    {"name": "Jazz Night Live", "url": "https://venue.in/jazz", "startDate": "2026-10-18T19:00:00+05:30", "location": {"name": "Venue"}},
]}


def test_listings_read_other_sources_by_day(tmp_path):
    (tmp_path / "venue.json").write_text(json.dumps(LISTINGS["2026-10-18"] + [{"name": "No date"}]))
    (tmp_path / "instagram.json").write_text(json.dumps([{"name": "Ours", "url": "u", "startDate": "2026-10-18"}]))
    assert instagram.listings(str(tmp_path / "*.json")) == LISTINGS


def test_matches_ask_jev_once_and_cache(db, monkeypatch):
    jev = FakeJev(({}, {"same": "1"}))
    monkeypatch.setattr(instagram, "TypeSafeClient", lambda: nullcontext(jev))
    monkeypatch.setenv("TYPESAFE_API_KEY", "key")
    event = {"name": "Jazz Night", "startDate": "2026-10-18T19:00:00+05:30"}
    pairs = [(post(), event)]
    assert instagram.matches(db, pairs, LISTINGS) == {"ABC": LISTINGS["2026-10-18"][1]}
    state, _ = jev.calls[0]
    assert state["event"] == {"name": "Jazz Night", "start": "2026-10-18T19:00:00+05:30"}
    assert instagram.matches(db, pairs, LISTINGS) == {"ABC": LISTINGS["2026-10-18"][1]}
    assert len(jev.calls) == 1
    assert instagram.matches(db, [(post(), event | {"startDate": "2026-10-19"})], LISTINGS) == {}


def test_describe_lists_name_time_and_venue():
    assert instagram.describe(LISTINGS["2026-10-18"][1]) == "Jazz Night Live | 19:00 | Venue"
    assert instagram.describe({"name": "Fair", "startDate": "2026-10-18"}) == "Fair | all day"


def expiring(hours):
    return f"https://cdn.example/a.jpg?oe={int((NOW + timedelta(hours=hours)).timestamp()):x}&oh=sig"


def test_events_use_the_first_live_image():
    result = {"nouls": DATED[0], "picks": {k: [v, 0.9] for k, v in DATED[1].items()}}
    live = post() | {"photos": [expiring(-1), expiring(5)]}
    assert instagram.to_event(live, result, NOW)["image"] == expiring(5)
    dead = post() | {"photos": [expiring(-1)]}
    assert "image" not in instagram.to_event(dead, result, NOW)


def test_account_of_skips_post_links():
    refreshed = record("ABC", discovery_input=None, input={"url": "https://www.instagram.com/p/ABC/"})
    assert instagram.account_of(refreshed) == "af_bangalore"


def test_refresh_keeps_the_account_and_marks_the_post_fresh(db):
    instagram.save(db, [record("ABC")], NOW - timedelta(days=4))
    collab = record("ABC", user_posted="partner", discovery_input=None, input={"url": "https://www.instagram.com/p/ABC/"})
    instagram.save(db, [collab], NOW)
    assert db.execute("SELECT account FROM posts").fetchall() == [("af_bangalore",)]
    assert db.execute("SELECT at FROM fetched").fetchall() == [(NOW.isoformat(),)]


def test_stale_picks_upcoming_events_fetched_three_days_ago(db):
    instagram.save(db, [record("OLD"), record("NEW"), record("NONE")], NOW - timedelta(days=3))
    instagram.save(db, [record("NEW")], NOW - timedelta(days=1))
    picks = {k: [v, 0.9] for k, v in DATED[1].items()}
    for code, nouls in [("OLD", DATED[0]), ("NEW", DATED[0]), ("NONE", {"event": 0.1})]:
        db.execute("INSERT INTO answers VALUES (?, ?, ?)", (code, instagram.VERSION, json.dumps({"nouls": nouls, "picks": picks})))
    posts = instagram.recent(db, ["af_bangalore"], NOW.date())
    assert instagram.stale(db, posts, NOW) == ["OLD"]


def test_collect_refreshes_stale_posts_by_url(db):
    api = FakeBrightData([record("OLD", discovery_input=None, input={"url": "https://www.instagram.com/p/OLD/"})], statuses=["ready"])
    instagram.collect(db, api, "key", [], NOW, ["OLD"])
    assert "discover_by" not in api.params[0]
    assert api.inputs == [{"url": "https://www.instagram.com/p/OLD/"}]
    assert db.execute("SELECT shortcode FROM fetched").fetchall() == [("OLD",)]
