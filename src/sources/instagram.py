import base64
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from glob import glob
from pathlib import Path

import requests
import yaml
from typesafe_sdk import Noul, TypeSafeClient, TypeSafeError

from src.common.jev import (
    MIN_CONFIDENCE,
    ask as ask_jev,
    clock,
    date_questions,
    end_clock,
    event_date,
    pick,
    time_questions,
    value,
)
from src.common.tz import IST

API = "https://api.brightdata.com/datasets/v3"
DATASET = "gd_lk5ns7kz21pck8jpis"
CACHE = Path.home() / ".cache" / "ingest-instagram.sqlite"
# Bump when a Jev question changes, so cached answers are asked again
VERSION = 2
REFRESH = timedelta(hours=20)
LOOKBACK = 45
OVERLAP = 2
MAX_POSTS = 30
MAX_IMAGES = 3
MAX_LISTINGS = 40
WAIT = 600
POLL = 15
STALE = timedelta(days=1)
IMAGES = {"TypeSafe-Danger-Zone-Images": "true"}
SUBJECT = "the announced event"
POST_RE = re.compile(r"instagram\.com/(?:[\w.]+/)?(?:p|reel|tv)/([\w-]+)")
ACCOUNT_RE = re.compile(r"instagram\.com/([\w.]+)")
EMOJI_RE = re.compile("[\U0001f000-\U0001faff☀-➿️‍|•]")
SKIP_RE = re.compile(
    r"^([#@]|hosted by|(event )?details\b|date\b|time\b|venue\b|when\b|where\b)"
    r"|link in (our )?bio|\bbookmyshow\b|\bregist(er|ration)\b|\btickets? (are )?(now )?live\b",
    re.IGNORECASE,
)
WHEN_RE = re.compile(
    r"\b(mon|tues?|wed|thur?s?|fri|sat|sun|(mon|tues|wednes|thurs|fri|satur|sun)day)\b|\b(jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec)\b"
    r"|\b(january|february|march|april|may|june|july|august|september|october|november|december)\b"
    r"|\b\d+(st|nd|rd|th|am|pm)?\b|\b(am|pm|onwards|from|to|at|and|till|until|ist)\b",
    re.IGNORECASE,
)


def log(*args):
    print("[INSTAGRAM]", *args, file=sys.stderr)


def accounts(path="in/known-hosts.yml"):
    with open(path) as f:
        return sorted({a.lower() for a in yaml.safe_load(f)["instagram"]})


def connect(path=CACHE):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS posts (shortcode TEXT PRIMARY KEY, account TEXT, pk TEXT, posted TEXT, record TEXT);
        CREATE TABLE IF NOT EXISTS accounts (account TEXT PRIMARY KEY, fetched TEXT);
        CREATE TABLE IF NOT EXISTS snapshots (id TEXT PRIMARY KEY, accounts TEXT, created TEXT);
        CREATE TABLE IF NOT EXISTS answers (shortcode TEXT PRIMARY KEY, version INTEGER, answers TEXT);
        CREATE TABLE IF NOT EXISTS matches (shortcode TEXT, listings TEXT, url TEXT, PRIMARY KEY (shortcode, listings));
        """
    )
    return db


def mdy(day):
    return day.strftime("%m-%d-%Y")


def due(db, names, now):
    fetched = dict(db.execute("SELECT account, fetched FROM accounts"))
    pending = {
        a
        for (names_,) in db.execute("SELECT accounts FROM snapshots")
        for a in json.loads(names_)
    }
    return [
        a
        for a in names
        if a not in pending
        and (a not in fetched or now - datetime.fromisoformat(fetched[a]) >= REFRESH)
    ]


def request(db, account, today):
    first = today - timedelta(days=LOOKBACK)
    row = db.execute(
        "SELECT fetched FROM accounts WHERE account = ?", (account,)
    ).fetchone()
    start = (
        max(first, date.fromisoformat(row[0][:10]) - timedelta(days=OVERLAP))
        if row
        else first
    )
    seen = db.execute(
        "SELECT pk FROM posts WHERE account = ? AND posted >= ? AND pk IS NOT NULL",
        (account, start.isoformat()),
    )
    return {
        "url": f"https://www.instagram.com/{account}/",
        "num_of_posts": MAX_POSTS,
        "posts_to_not_include": [pk for (pk,) in seen],
        "start_date": mdy(start),
        "end_date": mdy(today + timedelta(days=1)),
        "post_type": "post",
    }


def trigger(session, key, inputs):
    res = session.post(
        f"{API}/trigger",
        params={
            "dataset_id": DATASET,
            "type": "discover_new",
            "discover_by": "url",
            "include_errors": "true",
            "notify": "false",
        },
        headers={"Authorization": f"Bearer {key}"},
        json={"input": inputs},
        timeout=60,
    )
    if not res.ok:
        raise requests.HTTPError(f"{res.status_code} {res.text.strip()}", response=res)
    return res.json()["snapshot_id"]


def progress(session, key, snapshot):
    res = session.get(
        f"{API}/progress/{snapshot}",
        headers={"Authorization": f"Bearer {key}"},
        timeout=30,
    )
    res.raise_for_status()
    return res.json().get("status")


def download(session, key, snapshot):
    res = session.get(
        f"{API}/snapshot/{snapshot}",
        params={"format": "json"},
        headers={"Authorization": f"Bearer {key}"},
        timeout=120,
    )
    res.raise_for_status()
    return None if res.status_code == 202 else res.json()


def account_of(record):
    source = record.get("discovery_input") or record.get("input") or {}
    url = source.get("url") if isinstance(source, dict) else None
    match = ACCOUNT_RE.search(url or record.get("profile_url") or "")
    return (match.group(1) if match else record.get("user_posted") or "").lower()


def posted_on(record):
    return datetime.fromisoformat(record["date_posted"]).astimezone(IST).date()


def save(db, records):
    failed = set()
    for record in records:
        account = account_of(record)
        if code := record.get("error_code"):
            log(f"{account}: {code} {record.get('error', '')}")
            if code != "dead_page":
                failed.add(account)
        elif record.get("shortcode") and record.get("date_posted"):
            db.execute(
                "INSERT OR REPLACE INTO posts VALUES (?, ?, ?, ?, ?)",
                (
                    record["shortcode"],
                    account,
                    record.get("pk") or record.get("post_id"),
                    posted_on(record).isoformat(),
                    json.dumps(record, ensure_ascii=False),
                ),
            )
    return failed


def finish(db, session, key, snapshot, names, created):
    status = progress(session, key, snapshot)
    if status in ("failed", "canceled") or datetime.now(IST) - created > STALE:
        log(f"snapshot {snapshot} {status}, dropping it")
    elif status != "ready" or (records := download(session, key, snapshot)) is None:
        return False
    else:
        failed = save(db, records)
        db.executemany(
            "INSERT OR REPLACE INTO accounts VALUES (?, ?)",
            [(a, created.isoformat()) for a in names if a not in failed],
        )
        log(f"snapshot {snapshot}: {len(records)} records for {len(names)} accounts")
    db.execute("DELETE FROM snapshots WHERE id = ?", (snapshot,))
    db.commit()
    return True


def collect(db, session, key, names, now):
    if todo := due(db, names, now):
        inputs = [request(db, a, now.date()) for a in todo]
        snapshot = trigger(session, key, inputs)
        db.execute(
            "INSERT INTO snapshots VALUES (?, ?, ?)",
            (snapshot, json.dumps(todo), now.isoformat()),
        )
        db.commit()
        log(f"snapshot {snapshot} started for {len(todo)} accounts")
    deadline = time.monotonic() + WAIT
    while pending := db.execute(
        "SELECT id, accounts, created FROM snapshots"
    ).fetchall():
        for snapshot, names_, created in pending:
            finish(
                db,
                session,
                key,
                snapshot,
                json.loads(names_),
                datetime.fromisoformat(created),
            )
        if time.monotonic() > deadline:
            log(f"{len(pending)} snapshots still running, checking again next run")
            break
        time.sleep(POLL)


def to_post(record):
    photos = record.get("photos") or [
        c["url"]
        for c in record.get("post_content") or []
        if c.get("type") == "Photo" and c.get("url")
    ]
    return {
        "shortcode": record["shortcode"],
        "account": account_of(record),
        "caption": record.get("description") or "",
        "posted": posted_on(record),
        "photos": photos or [u for u in [record.get("thumbnail")] if u],
        "location": [p for p in record.get("location") or [] if isinstance(p, str)],
    }


def recent(db, names, today):
    rows = db.execute(
        "SELECT record FROM posts WHERE posted >= ? ORDER BY posted DESC",
        ((today - timedelta(days=LOOKBACK)).isoformat(),),
    )
    posts = (to_post(json.loads(r)) for (r,) in rows)
    return [p for p in posts if p["account"] in names]


def linked_elsewhere(pattern="out/*.json"):
    codes = set()
    for path in glob(pattern):
        if Path(path).name != "instagram.json":
            codes |= set(POST_RE.findall(Path(path).read_text(errors="ignore")))
    return codes


def listings(pattern="out/*.json"):
    by_day = defaultdict(list)
    for path in glob(pattern):
        if Path(path).name == "instagram.json":
            continue
        try:
            data = json.loads(Path(path).read_text())
        except ValueError:
            continue
        for e in data if isinstance(data, list) else []:
            if (
                isinstance(e, dict)
                and isinstance(e.get("startDate"), str)
                and e.get("name")
                and e.get("url")
            ):
                by_day[e["startDate"][:10]].append(e)
    return by_day


def candidates(event, by_day):
    # A busy day lists many events, so the ones at the same time come first
    found = by_day.get(event["startDate"][:10], [])
    return sorted(found, key=lambda o: o["startDate"] != event["startDate"])[
        :MAX_LISTINGS
    ]


def describe(listing):
    place = listing.get("location")
    venue = place.get("name") if isinstance(place, dict) else place
    parts = [str(listing["name"])[:150], listing["startDate"][11:16] or "all day"]
    return " | ".join(parts + ([str(venue)[:80]] if isinstance(venue, str) else []))


def same_listing(client, post, event, found):
    question = pick(
        "Which of these listings from other websites is the same event that this "
        "Instagram post announces?",
        {str(i): describe(o) for i, o in enumerate(found)},
    )
    announced = {"name": event["name"], "start": event["startDate"]}
    try:
        _, picks = ask_jev(
            client, state(post) | {"event": announced}, {"same": question}
        )
    except TypeSafeError as e:
        log(f"jev match failed for {post['shortcode']}: {e}")
        return False
    choice = value(picks, "same")
    return found[int(choice)]["url"] if choice else None


def matches(db, pairs, by_day):
    found, todo = {}, []
    for post, event in pairs:
        if not (listed := candidates(event, by_day)):
            continue
        key = hashlib.sha1("\n".join(sorted(o["url"] for o in listed)).encode())
        key = key.hexdigest()
        row = db.execute(
            "SELECT url FROM matches WHERE shortcode = ? AND listings = ?",
            (post["shortcode"], key),
        ).fetchone()
        if row:
            found[post["shortcode"]] = next(
                (o for o in listed if o["url"] == row[0]), None
            )
        else:
            todo.append((post, event, listed, key))
    log(f"{len(found)} matches cached, {len(todo)} to ask")
    if todo and os.environ.get("TYPESAFE_API_KEY"):
        with TypeSafeClient() as client, ThreadPoolExecutor(4) as pool:
            urls = pool.map(lambda t: same_listing(client, *t[:3]), todo)
            for (post, _, listed, key), url in zip(todo, urls):
                if url is not False:
                    db.execute(
                        "INSERT OR REPLACE INTO matches VALUES (?, ?, ?)",
                        (post["shortcode"], key, url),
                    )
                    found[post["shortcode"]] = next(
                        (o for o in listed if o["url"] == url), None
                    )
        db.commit()
    return found


def lines(caption):
    parts = (
        re.sub(r"\s+", " ", EMOJI_RE.sub(" ", l)).strip(" .,:-–*")
        for l in caption.splitlines()
    )
    return list(
        dict.fromkeys(
            p
            for p in parts
            if 3 <= len(p) <= 100 and not SKIP_RE.search(p) and not is_when(p)
        )
    )[:15]


def is_when(line):
    # A line that is only a date or a time is not a title
    return len(re.sub(r"[^a-z]", "", WHEN_RE.sub("", line.lower()))) < 3


def questions(post):
    return {
        "event": Noul(
            instructions="Does this Instagram post announce a specific event, such as a "
            "performance, workshop, screening, talk, walk or meetup, that the public "
            "can attend on a stated date? Calls for vendors, sponsors, applications or "
            "submissions, sales and product launches are not events."
        ),
        "name": pick(
            f"Which of these lines is the title of {SUBJECT}: the name of the show, "
            "workshop, talk or session itself, not its date, venue, host, a slogan or "
            "a call to action?",
            lines(post["caption"]),
        ),
        **date_questions(SUBJECT, post["posted"].year),
        **time_questions(SUBJECT),
    }


def state(post):
    return {
        "account": f"@{post['account']}",
        "posted_on": post["posted"].strftime("%A, %d %B %Y"),
        "caption": post["caption"],
    }


def enough(nouls, picks, post):
    return (
        nouls.get("event", 0) >= MIN_CONFIDENCE
        and event_date(picks, post["posted"]) is not None
    )


def image_asset(session, url):
    try:
        res = session.get(url, timeout=30)
        res.raise_for_status()
    except requests.RequestException as e:
        log(f"image failed: {e}")
        return None
    data = res.content
    if data[:3] == b"\xff\xd8\xff":
        fmt = "jpg"
    elif data[:8] == b"\x89PNG\r\n\x1a\n":
        fmt = "png"
    else:
        return None
    return {
        "type": "image",
        "format": fmt,
        "data_base64": base64.b64encode(data).decode("ascii"),
    }


def judge(client, session, post):
    asks = questions(post)
    try:
        nouls, picks = ask_jev(client, state(post), asks)
    except TypeSafeError as e:
        log(f"jev failed for {post['shortcode']}: {e}")
        return None
    used = 0
    # Captions often say little, so read the post's images until one gives a date
    for url in post["photos"][:MAX_IMAGES]:
        if enough(nouls, picks, post):
            break
        if not (image := image_asset(session, url)):
            continue
        ref = f"poster-{uuid.uuid4()}"
        try:
            nouls, picks = ask_jev(
                client,
                state(post) | {"poster": ref},
                asks,
                extra_body={"assets": {ref: image}},
                extra_headers=IMAGES,
            )
            used += 1
        except TypeSafeError as e:
            log(f"jev image failed for {post['shortcode']}: {e}")
    return {"nouls": nouls, "picks": picks, "images": used}


def answers(db, posts):
    cached = {
        code: json.loads(a)
        for code, a in db.execute(
            "SELECT shortcode, answers FROM answers WHERE version = ?", (VERSION,)
        )
    }
    todo = [p for p in posts if p["shortcode"] not in cached]
    log(f"{len(posts) - len(todo)} posts answered, {len(todo)} to ask")
    if todo and os.environ.get("TYPESAFE_API_KEY"):
        with (
            TypeSafeClient() as client,
            requests.Session() as session,
            ThreadPoolExecutor(4) as pool,
        ):
            for post, result in zip(
                todo, pool.map(lambda p: judge(client, session, p), todo)
            ):
                if result:
                    cached[post["shortcode"]] = result
                    db.execute(
                        "INSERT OR REPLACE INTO answers VALUES (?, ?, ?)",
                        (post["shortcode"], VERSION, json.dumps(result)),
                    )
        db.commit()
    return cached


def to_event(post, result):
    nouls, picks = result["nouls"], result["picks"]
    day = event_date(picks, post["posted"])
    if nouls.get("event", 0) < MIN_CONFIDENCE or not day:
        return None
    start, end = clock(picks, "start"), end_clock(nouls, picks)
    account = post["account"]
    event = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": value(picks, "name")
        or next(iter(lines(post["caption"])), f"Event by @{account}"),
        "url": f"https://www.instagram.com/p/{post['shortcode']}/",
        "description": post["caption"],
        "startDate": datetime.combine(day, start).isoformat()
        if start
        else day.isoformat(),
        "organizer": {
            "@type": "Organization",
            "name": f"@{account}",
            "url": f"https://www.instagram.com/{account}/",
        },
    }
    if end:
        event["endDate"] = datetime.combine(day, end).isoformat()
    if post["location"]:
        event["location"] = {
            "@type": "Place",
            "name": post["location"][0],
            "address": ", ".join(post["location"]),
        }
    return event


def events():
    now = datetime.now(IST)
    db = connect()
    names = accounts()
    if key := os.environ.get("BRIGHT_DATA_API_KEY"):
        try:
            collect(db, requests.Session(), key, names, now)
        except requests.RequestException as e:
            log(f"Bright Data failed, using cached posts: {e}")
    else:
        log("BRIGHT_DATA_API_KEY is not set, using cached posts")
    known = linked_elsewhere()
    posts = [p for p in recent(db, names, now.date()) if p["shortcode"] not in known]
    results = answers(db, posts)
    kept = {}
    # Posts are newest first, so a reminder post replaces the older announcement
    for post in posts:
        event = (r := results.get(post["shortcode"])) and to_event(post, r)
        if event and event["startDate"][:10] >= now.date().isoformat():
            _, same = kept.setdefault(
                (post["account"], event["startDate"]), (post, event)
            )
            if same is not event:
                same.setdefault("sameAs", []).append(event["url"])
    found = matches(db, kept.values(), listings())
    for post, event in kept.values():
        if listing := found.get(post["shortcode"]):
            # Sharing a link and start time lets dedup merge this into the listing
            log(f"{event['url']} is {listing['url']}")
            event["startDate"] = listing["startDate"]
            event.pop("endDate", None)
            event["sameAs"] = [listing["url"]] + event.get("sameAs", [])
    return [event for _, event in kept.values()]
