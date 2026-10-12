import functools
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "test/fixtures/e2e"
STEPS = {
    "allevents": ["src.sources", "allevents"],
    "build": ["src.build"],
    "processors": ["src.processors"],
    "sql": ["sqlite3", "events.db"],
    "tagger": ["src.tagger"],
    "dedup": ["src.dedup"],
}
QUIZ = "https://hornok.example/events/quiz-night"
QUIZ_COPY = "https://highape.com/bangalore/events/horn-ok-quiz-night-qn2030"
COSTLY = "https://highape.com/bangalore/events/royal-palace-weekend-retreat-rp2030"
POTTERY = "https://www.district.in/events/clay-and-chai-pottery-workshop-buy-tickets"
BIRDS = "https://walks.example/2030/bird-walk"
MYSURU = "https://walks.example/2030/mysuru-palace"
MOTHS = "https://walks.example/2030/monsoon-moths"
KIDS = "https://kids.example/little-explorers"
COMEDY = "https://comedy.example/shows/filter-coffee-chronicles"
CHESS = "https://chess.example/meetups/sunday"

pytestmark = pytest.mark.skipif(
    sqlite3.sqlite_version_info < (3, 38), reason="post-build.sql needs ->>"
)


@contextmanager
def serve(directory):
    handler = functools.partial(SimpleHTTPRequestHandler, directory=directory)
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()


def run(work, args, stdin):
    # A fresh env keeps API keys, proxies and the real HOME out; the seed fixes set order
    env = {
        "PATH": os.environ.get("PATH", os.defpath),
        "HOME": str(work / "home"),
        "PYTHONPATH": str(REPO),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONHASHSEED": "0",
        "NO_PROXY": "127.0.0.1,localhost",
    }
    done = subprocess.run(
        [sys.executable, "-m", *args], cwd=work, env=env, stdin=stdin,
        capture_output=True, text=True, timeout=120,
    )
    assert done.returncode == 0, f"{args}: {done.stderr}"
    return done


def mtimes():
    return {d: d.stat().st_mtime_ns for d in [REPO, *REPO.glob("src/**/")]}


@pytest.fixture(scope="module")
def pipeline(tmp_path_factory):
    work = tmp_path_factory.mktemp("e2e")
    for d in ("out", "patch"):
        shutil.copytree(FIXTURES / d, work / d)
    (work / "home/.cache").mkdir(parents=True)
    before = mtimes()
    with serve(FIXTURES / "pages") as base, open(REPO / "post-build.sql") as sql:
        urls = f"{base}/comedy.html\n\n{base}/missing.html\n{base}/chess.html\n"
        (work / "out/allevents.txt").write_text(urls)
        runs = {
            name: run(work, args, sql if name == "sql" else subprocess.DEVNULL)
            for name, args in STEPS.items()
        }
    conn = sqlite3.connect(work / "events.db")
    rows = conn.execute("SELECT url, event_json FROM events").fetchall()
    conn.close()
    return SimpleNamespace(
        work=work, base=base, runs=runs, touched=mtimes() != before,
        events={url: json.loads(event) for url, event in rows}, rows=rows,
    )


def keywords(pipeline, url):
    return set(pipeline.events[url]["keywords"])


def test_url_list_source(pipeline):
    run = pipeline.runs["allevents"]
    assert run.stdout.endswith("[ALLEVENTS] 2 events\n")
    assert f"Could not find event in {pipeline.base}/missing.html" in run.stdout
    listed = json.loads((pipeline.work / "out/allevents.json").read_text())
    assert [e["url"] for e in listed] == [COMEDY, CHESS]


def test_build_skips_bad_inputs(pipeline):
    assert "Event in out/manual.json has no URL" in pipeline.runs["build"].stdout


def test_final_events(pipeline):
    assert len(pipeline.rows) == 8
    assert set(pipeline.events) == {COMEDY, CHESS, QUIZ, POTTERY, BIRDS, MYSURU, MOTHS, KIDS}


def test_url_list_rows_use_the_json_ld_url(pipeline):
    comedy, chess = pipeline.events[COMEDY], pipeline.events[CHESS]
    assert comedy["url"] == COMEDY
    assert comedy["name"] == "Filter Coffee Chronicles | Stand-up Comedy Show"
    assert chess["@id"] == "https://chess.example/meetups/sunday#event"
    assert {"ALLEVENTS"} <= set(comedy["keywords"]) & set(chess["keywords"])


def test_processors(pipeline):
    run = pipeline.runs["processors"]
    assert f"[COSTLY] {COSTLY} dropped, cheapest ticket is 18000" in run.stdout
    assert "Modified 9 events, dropped 1" in run.stderr
    assert "ERROR" not in run.stderr and "[IMP]" not in run.stdout
    pottery = pipeline.events[POTTERY]
    assert pottery["name"] == "Clay & Chai Pottery Workshop"
    assert pottery["startDate"] == "2030-01-11T16:00:00+05:30"
    assert pottery["endDate"] == "2030-01-11T19:00:00+05:30"
    assert pottery["inLanguage"] == {"@type": "Language", "name": "English", "alternateName": "en"}
    assert pottery["typicalAgeRange"] == "16+"
    assert pottery["@type"] == "EducationEvent"
    assert pipeline.events[KIDS]["endDate"] == "2030-01-18T12:00:00+05:30"
    assert {"NOTINBLR"} <= keywords(pipeline, MYSURU)
    assert {"FREE", "LASTCALL"} <= keywords(pipeline, BIRDS)
    assert {"PRICEY"} <= keywords(pipeline, POTTERY)


def test_patch_and_venue_files(pipeline):
    quiz = pipeline.events[QUIZ]
    assert quiz["organizer"]["name"] == "Horn OK Collective"
    assert quiz["inLanguage"] == "en"
    geo = quiz["location"]["geo"]
    assert (geo["latitude"], geo["longitude"]) == (12.9784, 77.6408)
    assert quiz["@type"] == "SocialEvent"


def test_post_build_sql(pipeline):
    run = pipeline.runs["sql"]
    assert "Error" not in run.stdout + run.stderr
    assert "SQLITE_" not in run.stdout + run.stderr
    assert {"HSR"} <= keywords(pipeline, BIRDS)
    assert {"INDIRANAGAR"} <= keywords(pipeline, QUIZ)
    assert {"ONLINE"} <= keywords(pipeline, MOTHS)
    assert {"CBD"} <= keywords(pipeline, COMEDY)
    assert pipeline.events[POTTERY]["keywords"].count("HSR") == 1


def test_tagger(pipeline):
    assert "tagged 7 and typed 0 of 9 events" in pipeline.runs["tagger"].stderr
    assert (pipeline.work / "home/.cache/ingest-activities.sqlite").exists()
    assert {"QUIZZING"} <= keywords(pipeline, QUIZ)
    assert {"BIRDING", "NATURE-WALK"} <= keywords(pipeline, BIRDS)
    assert {"POTTERY"} <= keywords(pipeline, POTTERY)
    assert {"KIDS"} <= keywords(pipeline, KIDS)
    assert {"STANDUP-COMEDY"} <= keywords(pipeline, COMEDY)
    assert {"CHESS"} <= keywords(pipeline, CHESS)
    assert "HERITAGE-WALK" not in keywords(pipeline, MYSURU)


def test_dedup(pipeline):
    out = pipeline.runs["dedup"].stdout
    assert f"[DEDUP] {QUIZ_COPY} -> {QUIZ}" in out
    assert "[DEDUP] Removed 1 duplicate events" in out
    quiz = pipeline.events[QUIZ]
    assert quiz["sameAs"] == [QUIZ_COPY]
    assert {"HORNOK", "HIGHAPE", "Quiz", "BUDGET"} <= set(quiz["keywords"])
    assert "FREE" not in quiz["keywords"]
    assert [o["price"] for o in quiz["offers"]] == ["300"]


def test_invariants(pipeline):
    for url, event in pipeline.events.items():
        assert len(event["keywords"]) == len(set(event["keywords"])), url
        assert event["startDate"].startswith("2030-01-"), url
    files = {str(p.relative_to(pipeline.work)) for p in pipeline.work.rglob("*") if p.is_file()}
    copied = {str(p.relative_to(FIXTURES)) for d in ("out", "patch") for p in (FIXTURES / d).iterdir()}
    assert files == copied | {
        "events.db",
        "out/allevents.txt",
        "out/allevents.json",
        "home/.cache/event-fetcher-cache.sqlite",
        "home/.cache/ingest-activities.sqlite",
    }
    assert not pipeline.touched
