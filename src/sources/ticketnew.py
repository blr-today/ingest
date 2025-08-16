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
MOVIE_KEYS = ["title", "censorRating", "runtime", "movieId", "genres", "image"]
MOVIE_SCREEN_FORMATS = {}

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
    "format",
    "availability",
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


def fetch_movies(movie_list):
    movies = []
    codes = []
    for movie_detail in movie_list:
        movie = {
            "title": movie_detail["label"],
            "movieId": movie_detail["contentId"],
            "censorRating": movie_detail["censor"],
            "runtime": movie_detail["duration"],
            "genres": ", ".join(movie_detail["grn"]),
            "image": movie_detail["appImgPath"],
            "formats": [],
        }

        for lang in movie_detail["languageFormatGroups"]:
            movie["formats"].append(
                {
                    "lang": LANGUAGE_TO_ISO_MAP[lang["lang"]],
                    "id": lang["fmtGrpId"],
                    "screenFormats": [],
                }
            )
            for screenFormat in lang["screenFormats"]:
                movie["formats"][-1]["screenFormats"].append(
                    {
                        "id": screenFormat["movieCode"],
                        "name": screenFormat["scrnFmt"],
                        "earliestDate": screenFormat["nextAvailableDate"],
                    }
                )

        movies.append(movie)

    return movies


def parse_show_data(shows_per_day, shows, movie):
    def reverse_lookup_format(mid):
        for formatData in movie["formats"]:
            for screenFormat in formatData["screenFormats"]:
                if screenFormat["id"] == mid:
                    return screenFormat["name"]
        return None

    def reverse_lookup_lang(fid):
        for formatData in movie["formats"]:
            if formatData["id"] == fid:
                return formatData["lang"]
        return None

    for cinema in shows_per_day.values():
        for details in cinema:
            # print(details)
            language = reverse_lookup_lang(details["fid"])
            availability = sum(area["sAvail"] for area in details["areas"])
            if availability > 0:
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
                        "movieId": movie["movieId"],
                        "format": reverse_lookup_format(details["mid"]),
                        "language": language,
                        "availability": availability,
                    }
                )


def fetch_shows(session, movies):
    shows = []

    for movie in movies:
        for formatData in movie["formats"]:
            code = formatData["id"]
            res = make_request(session, SHOWS_PATH, {"movieCode": code, "reqData": "1"})
            # Movie is not playing really
            if "sessionDates" in res["data"]:
                for show_date in res["data"]["sessionDates"]:
                    res = make_request(
                        session,
                        SHOWS_PATH,
                        {
                            "movieCode": code,
                            "date": show_date,
                            "reqData": "1",
                            "meta": "1",
                        },
                    )

                    try:
                        shows_per_day = res["pageData"]["sessions"]
                        movieInfo = res["meta"]["movies"][0]
                        parse_show_data(shows_per_day, shows, movie)
                    except KeyError as e:
                        print(e)
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


"""
Update shows so it only has shows with unique
movieId,theatreId,screenName,language,startTime combination
combination
"""


def unique_shows(show):
    unique = {}
    for s in show:
        key = (
            s["movieId"],
            s["theatreId"],
            s["screenName"],
            s["language"],
            s["startTime"],
        )
        if key not in unique:
            unique[key] = s
    return list(unique.values())


def main():
    session = get_cached_session()
    cinemas = fetch_cinemas(session)

    movie_list = fetch_movie_list(session)
    movies = fetch_movies(movie_list)

    shows = fetch_shows(session, movies)

    with (
        open("out/ticketnew/movies.json", "w", newline="") as movies_file,
        open("out/ticketnew/sessions.csv", "w", newline="") as sessions_file,
        open("out/ticketnew/cinemas.csv", "w", newline="") as cinemas_file,
    ):
        session_writer = csv.DictWriter(sessions_file, fieldnames=SHOW_KEYS)

        cinema_writer = csv.DictWriter(
            cinemas_file, fieldnames=CINEMA_KEYS, extrasaction="ignore"
        )

        movies_file.write(json.dumps(movies, indent=4))

        session_writer.writeheader()
        session_writer.writerows(unique_shows(shows))

        cinema_writer.writeheader()
        cinema_writer.writerows(cinemas)

    print(f"[TicketNew] {len(cinemas)} cinemas")
    print(f"[TicketNew] {len(movies)} movies")


if __name__ == "__main__":
    main()
