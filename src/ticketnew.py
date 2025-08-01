import json
from common.session import get_cached_session
from datetime import datetime
import sys
import csv

BASE_URL = "https://apiproxy.paytm.com/v3/movies/search"
MOVIE_LIST_PATH = "/movies"
SHOWS_PATH = "/movie"
CINEMA_PATH = "/cinemas"

QUERY_PARAMS = {"city": "bengaluru"}

# Keys for csv files
MOVIE_KEYS = ["title", "censorRating", "runtime", "movieId"]

LANGUAGE_TO_ISO_MAP = {
    "Assamese": "as",
    "Bengali": "bn",
    "English": "en",
    "Gujarati": "gu",
    "Hindi": "hi",
    "Hinglish": "hi",
    "Japanese": "ja",
    "Kannada": "kn",
    "Kashmiri": "ks",
    "Malayalam": "ml",
    "Marathi": "mr",
    "Nepali": "ne",
    "Odia": "or",
    "Punjabi": "pa",
    "Sanskrit": "sa",
    "Sindhi": "sd",
    "Tamil": "ta",
    "Telugu": "te",
    "Urdu": "ur",
    "Korean": "ko",
}

CINEMA_KEYS = [
    "theatreId",
    "name",
    "cityName",
    "address",
    "latitude",
    "longitude",
]

SHOW_KEYS = [
    "movieId",
    "theatreId",
    "totalSeats",
    "availableSeats",
    "screenName",
    "language",
    "startTime",
    "endTime",
]


def make_request(session, path, query={}):
    url = f"{BASE_URL}{path}"
    res = session.get(url, params=QUERY_PARAMS | query)
    try:
        return res.json()
    except:
        print(f"[TicketNew] Failed to fetch {url} with params {query}", file=sys.stderr)
        print(res.text, file=sys.stderr)
        raise ValueError("Invalid response from TicketNew API")


def fetch_movie_list(session):
    res = make_request(session, MOVIE_LIST_PATH, {"mdp": "1"})
    return res["data"]["groupedMovies"]


# Codes are movie codes which coresponde to movie in a specific language. Required to fetch movie details


def fetch_movies_and_codes(movie_list):
    movies = []
    codes = []
    for movie_detail in movie_list:
        movie = {
            "title": movie_detail["label"],
            "movieId": movie_detail["contentId"],
            "censorRating": movie_detail["censor"],
            "runtime": movie_detail["duration"],
        }

        codes += list(
            map(lambda x: x["fmtGrpId"], movie_detail["languageFormatGroups"])
        )

        movies.append(movie)

    return [movies, codes]

def parse_show_data(shows_per_day, shows, movieInfo):
    for cinema in shows_per_day.values():
        for details in cinema:
            language = movieInfo["lang"]
            if language not in LANGUAGE_TO_ISO_MAP:
                print(f"[TICKETNEW] Unknown language: {language}", file=sys.stderr)
            shows.append(
                {
                    "theatreId": details["cid"],
                    "startTime": datetime.strptime(
                        details["showTime"], "%Y-%m-%dT%H:%M"
                    ).isoformat(),
                    "endTime": datetime.strptime(
                        details["closeTime"], "%Y-%m-%dT%H:%M"
                    ).isoformat(),
                    "availableSeats": details["avail"],
                    "totalSeats": details["total"],
                    "screenName": details["audi"],
                    "movieId": movieInfo["contentId"],
                    "language": LANGUAGE_TO_ISO_MAP.get(
                        language,
                        language
                    )
                }
            )

def fetch_shows(session, codes):
    shows = []

    for code in codes:
        res = make_request(
            session, SHOWS_PATH, {"movieCode": code, "reqData": "1"}
        )
        # Movie is not playing really
        if 'sessionDates' in res['data']:
            for show_date in res["data"]["sessionDates"]:
                res = make_request(
                    session,
                    SHOWS_PATH,
                    {"movieCode": code, "fromdate": show_date, "reqData": "1", "meta": "1"},
                )

                try:
                    shows_per_day = res["pageData"]["sessions"]
                    movieInfo = res['meta']['movies'][0]
                    parse_show_data(shows_per_day, shows, movieInfo)
                except KeyError as e:
                    print(res.keys())
                    print(res)
                    shows_per_day = []
                    continue
        
    return shows


"""
List of cinemas can be found using a single API call.
"""


def fetch_cinemas(session):
    return [
        {
            "theatreId": cinema["id"],
            "name": cinema["name"],
            "cityname": cinema["city"],
            "address": cinema["address"],
            "latitude": cinema["lat"],
            "longitude": cinema["lon"],
        }
        for cinema in make_request(session, CINEMA_PATH)["data"]["cinemas"]
    ]


def main():
    session = get_cached_session()
    cinemas = fetch_cinemas(session)

    movie_list = fetch_movie_list(session)
    movies, codes = fetch_movies_and_codes(movie_list)

    shows = fetch_shows(session, codes)

    with (
        open("out/ticketnew-movies.csv", "w", newline="") as movies_file,
        open("out/ticketnew-sessions.csv", "w", newline="") as sessions_file,
        open("out/ticketnew-cinemas.csv", "w", newline="") as cinemas_file,
    ):
        movie_writer = csv.DictWriter(movies_file, fieldnames=MOVIE_KEYS)

        session_writer = csv.DictWriter(sessions_file, fieldnames=SHOW_KEYS)

        cinema_writer = csv.DictWriter(
            cinemas_file, fieldnames=CINEMA_KEYS, extrasaction="ignore"
        )

        movie_writer.writeheader()
        movie_writer.writerows(movies)

        session_writer.writeheader()
        session_writer.writerows(shows)

        cinema_writer.writeheader()
        cinema_writer.writerows(cinemas)

    print(f"[TicketNew] {len(cinemas)} cinemas")
    print(f"[TicketNew] {len(movies)} movies")


if __name__ == "__main__":
    main()
