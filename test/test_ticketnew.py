import csv
import json
from pathlib import Path

import pytest

import ticketnew

FIXTURES = Path(__file__).parent / "fixtures" / "ticketnew"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


class FakeResponse:
    def __init__(self, data):
        self.data = data
        self.text = json.dumps(data)

    def json(self):
        if self.data is None:
            raise ValueError("not json")
        return self.data


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, params=None):
        self.calls.append((url.removeprefix(ticketnew.BASE_URL), params))
        path = url.removeprefix(ticketnew.BASE_URL)
        if path == ticketnew.CINEMA_PATH:
            return FakeResponse(load("cinemas"))
        if path == ticketnew.MOVIE_LIST_PATH:
            return FakeResponse(load("movies"))
        name = f"movie-{params['movieCode']}-{params.get('date', '2026-10-13')}"
        if (FIXTURES / f"{name}.json").exists():
            return FakeResponse(load(name))
        return FakeResponse({"data": {}})


@pytest.fixture
def movies():
    return {m["title"]: m for m in ticketnew.fetch_movies(ticketnew.fetch_movie_list(FakeSession()))}


def test_requests_carry_city():
    session = FakeSession()
    ticketnew.fetch_movie_list(session)
    assert session.calls == [("/movies", {"city": "bengaluru", "mdp": "1"})]


def test_bad_response_raises(capsys):
    session = FakeSession()
    session.get = lambda url, params=None: FakeResponse(None)
    with pytest.raises(ValueError, match="Invalid response"):
        ticketnew.make_request(session, "/movies")
    assert "Failed to fetch" in capsys.readouterr().err


def test_movies_group_languages_and_formats(movies):
    jailer = movies["Jailer 2"]
    assert jailer["movieId"] == 187766
    assert [f["lang"] for f in jailer["formats"]] == ["ta", "kn", "te"]
    assert [s["name"] for s in jailer["formats"][0]["screenFormats"]] == ["2D", "IMAX 2D"]
    assert jailer["formats"][0]["screenFormats"][0]["earliestDate"] == "2026-10-15"
    assert movies["Kitti"]["genres"] == "Thriller"
    assert movies["Kitti"]["censorRating"] == "UA16+"


def test_cinemas():
    cinemas = ticketnew.fetch_cinemas(FakeSession())
    assert len(cinemas) == 3
    assert {c["cityName"] for c in cinemas} == {"Bengaluru"}
    assert all(c["latitude"] and c["longitude"] for c in cinemas)


def test_parse_show_data(movies):
    shows = []
    sessions = load("movie-36nydr19vse-2026-10-13")["pageData"]["sessions"]
    ticketnew.parse_show_data(sessions, shows, movies["Kitti"])
    first = next(s for s in shows if s["theatreId"] == 52080)
    assert first["startTime"] == "2026-10-13T10:35:00"
    assert first["endTime"] == "2026-10-13T12:34:00"
    assert first["format"] == "2D"
    assert first["language"] == "ta"
    assert first["screenName"] == "SCREEN 1"
    assert (first["availableSeats"], first["totalSeats"], first["availability"]) == (177, 179, 177)
    assert len(shows) == 3


def test_end_time_is_left_out_without_runtime(movies):
    shows = []
    sessions = load("movie-36nydr19vse-2026-10-13")["pageData"]["sessions"]
    ticketnew.parse_show_data(sessions, shows, dict(movies["Kitti"], runtime=None))
    assert {s["endTime"] for s in shows} == {None}


def test_full_shows_are_skipped(movies):
    shows = []
    sessions = load("movie-36nydr19vse-2026-10-13")["pageData"]["sessions"]
    for show in sessions["52080"]:
        for area in show["areas"]:
            area["sAvail"] = 0
    ticketnew.parse_show_data(sessions, shows, movies["Kitti"])
    assert {s["theatreId"] for s in shows} == {1039754, 10940}


def test_fetch_shows_walks_session_dates(movies, capsys):
    session = FakeSession()
    shows = ticketnew.fetch_shows(session, [movies["Kitti"], movies["Jailer 2"]])
    assert len(shows) == 3
    dated = [p["date"] for _, p in session.calls if p and "date" in p]
    assert dated == ["2026-10-13", "2026-10-14"]
    assert "pageData" in capsys.readouterr().out


def test_unique_shows():
    show = {"movieId": 1, "theatreId": 2, "screenName": "A", "language": "en", "startTime": "t", "availability": 3}
    assert ticketnew.unique_shows([show, dict(show, availability=1), dict(show, screenName="B")]) == [
        show, dict(show, screenName="B")]


def test_main_writes_outputs(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "out" / "ticketnew").mkdir(parents=True)
    monkeypatch.setattr(ticketnew, "get_cached_session", FakeSession)
    ticketnew.main()
    out = tmp_path / "out" / "ticketnew"
    assert len(json.loads((out / "movies.json").read_text())) == 3
    sessions = list(csv.DictReader((out / "sessions.csv").open()))
    assert {r["movieId"] for r in sessions} == {"231756"}
    cinemas = list(csv.DictReader((out / "cinemas.csv").open()))
    assert [c["cityName"] for c in cinemas] == ["Bengaluru"] * 3
    assert "[TicketNew] 3 movies" in capsys.readouterr().out
