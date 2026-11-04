import json
import logging
import os
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from typesafe_sdk import Choice, Noul, TypeSafeClient, TypeSafeError

from src.common.activities import (
    EXCLUDE,
    QUESTIONS,
    TAGS,
    THRESHOLDS,
    TYPE_CONFIDENCE,
    TYPES,
    VERSION,
    with_parents,
)

logging.basicConfig(level=logging.INFO, format="[TAGGER] %(message)s")
log = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("typesafe_sdk").setLevel(logging.WARNING)

SOURCES = {
    "All",
    "BOOKMYSHOW",
    "DISTRICT",
    "URBANAUT",
    "HIGHAPE",
    "INSIDER",
    "ALLEVENTS",
}
# Tags we classify but do not want to show
DEMOTE = {
    "LIVE-MUSIC/DEVOTIONAL": "LOW-QUALITY",
    "EXPO": "LOW-QUALITY",
    "ATTRACTION": "LOW-QUALITY",
    "PROMOTION": "LOW-QUALITY",
    "NIGHTLIFE": "LOW-QUALITY",
    "FITNESS/PILATES": "-CURATED",
    "TRIP": "NOTINBLR",
    "TECH": "BUSINESS",
}
# Demoted without a trace, since the tag itself is not worth showing
REPLACED = {"TECH"}
# These outlets rerun mass-produced craft sessions, but host good gigs too
CRAFT_SPAM_VENUES = ("koramangala social", "indiranagar social")
CACHE = Path.home() / ".cache" / "ingest-activities.sqlite"
CLASS = r"(workshop|class|jam|intensive|lab)"
SCREENING = r"\b(screening|live on|watch party|screened)\b"
RULES = [
    (
        "SPORTS-SCREENING/F1",
        rf"(\bf1\b|formula ?1|grand prix).*{SCREENING}|{SCREENING}.*(\bf1\b|formula ?1|grand prix)",
    ),
    ("SPORTS-SCREENING/CRICKET", rf"\bipl\b.*{SCREENING}|{SCREENING}.*\bipl\b"),
    (
        "SPORTS-SCREENING/CRICKET",
        rf"(cricket|india vs|\bt20\b|\bodi\b).*{SCREENING}|{SCREENING}.*(cricket|india vs)",
    ),
    (
        "SPORTS-SCREENING/FOOTBALL",
        rf"(premier league|champions league|la liga|el clasico|football|\bfifa\b).*{SCREENING}|{SCREENING}.*(premier league|champions league|football)",
    ),
    ("GAMES/QUIZ", r"\bquiz|\btrivia\b"),
    ("GAMES/CHESS", r"\bchess\b"),
    ("ART-CRAFT/KINTSUGI", r"\bkintsugi\b"),
    ("ART-CRAFT/RESIN", r"\bresin\b|\bepoxy\b"),
    ("ART-CRAFT/POTTERY", r"\bpottery\b|\bceramics?\b|\bwheel throwing\b"),
    ("ART-CRAFT/CANDLES", r"\bcandle making\b|\bmake your own candle"),
    ("ART-CRAFT/PERFUMERY", r"\bperfum|\bsoap making\b"),
    ("ART-CRAFT/CALLIGRAPHY", r"\bcalligraphy\b|\blettering\b"),
    ("ART-CRAFT/PRINTMAKING", r"\blino ?cut|\bblock print|\bcyanotype|\bprintmaking\b"),
    (
        "ART-CRAFT/PAINTING",
        r"\bsip (and|&|n) paint\b|\bwatercolou?r|\bsketch(ing)?\b(?! comedy)|\bcanvas painting\b",
    ),
    ("ON-STAGE/IMPROV", rf"(?<!dance )\bimprov\w* {CLASS}"),
    ("SHOW/IMPROV", rf"(?<!dance )\bimprov\b(?!\w* {CLASS})"),
    ("ON-STAGE/ACTING", r"\bacting (workshop|intensive|class)|\bintro to acting\b"),
    ("SHOW/STANDUP", r"\bcomedy show\b|\bstand-?up comedy\b"),
    ("SHOW/STORYTELLING", r"\bstorytelling\b"),
    ("ON-STAGE/OPEN-MIC", r"\bopen mic\b"),
    ("NIGHTLIFE/KARAOKE", r"\bkaraoke\b"),
    (
        "GAMES/SOCIAL-DEDUCTION",
        r"\bmafia\b|\bwerewolf\b|\bsocial deduction\b|\bclocktower\b|\bbotc\b",
    ),
    ("GAMES/TTRPG", r"\bd ?& ?d\b|\bdungeons (and|&) dragons\b|\bttrpg"),
    ("GAMES/BOARDGAMES", r"\bboard ?games?\b|\btabletop\b"),
    ("FITNESS/RUNNING", r"\brun club\b|\bmarathon\b|\b(5|10|21) ?k run\b"),
    ("FITNESS/YOGA", r"\byoga\b"),
    ("FITNESS/PILATES", r"\bpilates\b"),
    ("DANCING/GARBA", r"\bgarba\b(?!.*\b(necklace|jewell?ery|making)\b)"),
    ("DANCING/LATIN", r"\bsalsa\b|\bbachata\b|\bkizomba\b"),
    ("OUTDOORS/BIRDING", r"\bbird ?(walk|watching)\b|\bbirding\b"),
    ("OUTDOORS/HERITAGE-WALK", r"\bheritage walk\b|\bwalking tour\b"),
    ("BOOKS/BOOK-CLUB", r"\bbook club\b|\bread together\b"),
    ("BOOKS/AUTHOR-TALK", r"\bbook (launch|signing)\b"),
]
SPORTS = {"SPORTS-SCREENING/F1", "SPORTS-SCREENING/CRICKET", "SPORTS-SCREENING/FOOTBALL"}


def keywords(event):
    kw = event.get("keywords")
    return kw if isinstance(kw, list) else []


def sports_screening(event):
    name = str(event.get("name") or "").lower()
    kw = "\n".join(map(str, keywords(event))).lower()
    description = str(event.get("description") or "")
    ipl = (
        re.search(r"\b(live ipl|ipl live)", name)
        or "ipl screening" in kw
        or ("live session & streaming" in kw and "sports" in kw)
        or ("screening" in kw and re.search(r"\bipl\b", description, re.I))
    )
    f1 = re.search(r"\b(f1|formula 1) live", name) or re.search(
        r"f1 screening|grand prix|screening of (f1|formula ?1)", kw
    )
    return bool(ipl or (f1 and "screening" in json.dumps(event).lower()))


def by_rules(event):
    name = str(event.get("name") or "").lower()
    tags = {tag for tag, pattern in RULES if re.search(pattern, name)}
    if not tags & SPORTS:
        if event.get("@type") == "ScreeningEvent":
            tags.add("MOVIE-SCREENING")
        if sports_screening(event):
            tags.add("SPORTS-SCREENING")
    if event.get("@type") == "ChildrensEvent":
        tags.add("KIDS")
    if "SISTERSINSWEAT" in keywords(event):
        tags.add("WOMEN-ONLY")
    return tags


def state(event):
    organizer, venue = event.get("organizer"), event.get("location")
    name = event.get("name")
    return {
        "event": {
            "name": name,
            "type": event.get("@type"),
            "organizer": organizer.get("name") if isinstance(organizer, dict) else None,
            "venue": venue.get("name") if isinstance(venue, dict) else None,
            "keywords": [k for k in keywords(event) if k not in SOURCES and k != name],
            "description": re.sub(r"\s+", " ", str(event.get("description") or ""))[
                :600
            ],
        }
    }


def ask(client, event):
    questions = {tag: Noul(instructions=q) for tag, q in QUESTIONS.items()}
    questions["@type"] = Choice(
        instructions="Which kind of event is this?",
        criteria=TYPES | {"Event": "None of these fits"},
    )
    try:
        response = client.system_one(state=state(event), questions=questions)
    except TypeSafeError as e:
        log.warning("jev failed for %s: %s", event.get("url"), e)
        return None
    answers = {k: a.noul for k, a in response.nouls.items()}
    kind = response.choices["@type"]
    return answers | {"@type": [kind.choice, kind.confidence]}


def by_jev(events):
    db = sqlite3.connect(CACHE)
    db.execute(
        "CREATE TABLE IF NOT EXISTS answers (url TEXT PRIMARY KEY, version INTEGER, nouls TEXT)"
    )
    cached = {
        u: json.loads(n)
        for u, n in db.execute(
            "SELECT url, nouls FROM answers WHERE version = ?", (VERSION,)
        )
    }
    todo = {url: event for url, event in events.items() if url not in cached}
    log.info("%d events cached, %d to ask", len(events) - len(todo), len(todo))
    if todo and os.environ.get("TYPESAFE_API_KEY"):
        with TypeSafeClient() as client, ThreadPoolExecutor(8) as pool:
            for url, nouls in zip(
                todo, pool.map(lambda e: ask(client, e), todo.values())
            ):
                if nouls:
                    cached[url] = nouls
                    db.execute(
                        "INSERT OR REPLACE INTO answers VALUES (?, ?, ?)",
                        (url, VERSION, json.dumps(nouls)),
                    )
        db.commit()
    return {url: answers for url, answers in cached.items() if url in events}


def jev_tags(answers):
    return {t for t, p in answers.items() if t in QUESTIONS and p >= THRESHOLDS.get(t, 0.5)}


def jev_type(answers):
    kind, confidence = answers.get("@type", ("Event", 0))
    return kind if kind in TYPES and confidence >= TYPE_CONFIDENCE else None


def event_tags(event, answers):
    # post-build.sql tags some events too, and they need their parents
    tags = by_rules(event) | jev_tags(answers) | (set(keywords(event)) & set(TAGS))
    # Game nights pass as plays on BMS, and as stranger meetups by their pitch
    if any(t.startswith("GAMES/") for t in tags):
        tags -= {"SHOW/THEATER", "SOCIAL/STRANGERS-MEETUP"}
    tags = with_parents(tags)
    venue = (state(event)["event"]["venue"] or "").lower()
    if "ART-CRAFT" in tags and venue.startswith(CRAFT_SPAM_VENUES):
        tags.add("LOW-QUALITY")
    return (tags | {DEMOTE[t] for t in tags if t in DEMOTE}) - REPLACED


def main():
    conn = sqlite3.connect("events.db")
    rows = conn.execute("SELECT rowid, url, event_json FROM events").fetchall()
    events = {}
    for rowid, url, event_json in rows:
        event = json.loads(event_json)
        if not EXCLUDE & set(keywords(event)):
            events.setdefault(url, []).append((rowid, event))
    jev = by_jev({url: dates[0][1] for url, dates in events.items()})
    tagged = typed = 0
    for url, dates in events.items():
        answers = jev.get(url, {})
        for rowid, event in dates:
            kind = jev_type(answers)
            retype = event.get("@type") in (None, "Event") and kind
            if retype:
                event["@type"] = kind
                typed += 1
            tags = event_tags(event, answers)
            new = sorted(tags - set(keywords(event)))
            if new:
                event["keywords"] = keywords(event) + new
            if new or retype:
                conn.execute(
                    "UPDATE events SET event_json = ? WHERE rowid = ?",
                    (json.dumps(event), rowid),
                )
                tagged += bool(new)
    conn.commit()
    log.info("tagged %d and typed %d of %d events", tagged, typed, len(rows))


if __name__ == "__main__":
    main()
