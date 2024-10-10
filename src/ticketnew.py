import json
from common.session import get_cached_session
from datetime import datetime
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
    "English": "en",
    "Hindi": "hi",
    "Hinglish": "hi",
    "Japanese": "ja",
    "Kannada": "kn",
    "Malayalam": "ml",
    "Marathi": "mr",
    "Tamil": "ta",
    "Telugu": "te",
    "Odia": "or",
    "Punjabi": "pa",
    "Gujarati": "gu",
    "Bengali": "bn",
    "Kashmiri": "ks",
    "Sanskrit": "sa",
    "Sindhi": "sd",
    "Urdu": "ur",
    "Nepali": "ne",
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
    return session.get(url, params=QUERY_PARAMS | query).json()


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


def fetch_shows(session, codes):
    shows = []

    for code in codes:
        show_dates = make_request(
            session, SHOWS_PATH, {"movieCode": code, "reqData": "1"}
        )["data"]["sessionDates"]

        # Fetch shows for all the available future dates
        for show_date in show_dates:
            show_data = make_request(
                session,
                SHOWS_PATH,
                {"movieCode": code, "fromdate": show_date, "reqData": "1", "meta": "1"},
            )

            shows_per_day = show_data["pageData"]["sessions"]

            for cinema in shows_per_day.values():
                for details in cinema:
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
                            "movieId": show_data["meta"]["movies"][0]["contentId"],
                            "language": LANGUAGE_TO_ISO_MAP.get(
                                show_data["meta"]["movies"][0]["lang"],
                                show_data["meta"]["movies"][0]["lang"]
                            )
                        }
                    )

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
