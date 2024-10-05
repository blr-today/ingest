import json
from common.session import get_cached_session
from datetime import datetime
import csv

BASE_URL = 'https://apiproxy.paytm.com/v3/movies/search'
MOVIE_LIST_PATH = '/movies?version=3&site_id=6&channel=HTML5&child_site_id=370&client_id=ticketnew&clientId=ticketnew&city=bengaluru&mdp=1'
SHOWS_PATH = '/movie?meta=1&city=bengaluru&reqData=1&version=3&site_id=6&channel=HTML5&child_site_id=370&client_id=ticketnew&clientId=ticketnew&movieCode='
CINEMA_PATH = '/cinemas?version=3&site_id=6&channel=HTML5&child_site_id=370&client_id=ticketnew&clientId=ticketnew&city=bengaluru'

# Keys for csv files
MOVIE_KEYS = [
    "title",
    "censorRating",
    "runtime",
    "movieId"    
]

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
    "endTime"
]

def fetch_movie_list(session):
    res = session.get(f"{BASE_URL}{MOVIE_LIST_PATH}").json()
    return res['data']['groupedMovies']

# Codes are movie codes which coresponde to movie in a specific language. Required to fetch movie details
def fetch_movies_and_codes(movie_list):
    movies = []
    codes = []
    for movie_detail in movie_list:
        movie = {
            'title': movie_detail['label'],
            'movieId': movie_detail['contentId'],
            'censorRating': movie_detail['censor'],
            'runtime': movie_detail['duration'],
        }

        codes += list(map(lambda x: x['fmtGrpId'], movie_detail['languageFormatGroups'])) 

        movies.append(movie)

    return [movies, codes]

def fetch_shows(session, codes):
    shows = []

    for code in codes:
        res = session.get(f"{BASE_URL}{SHOWS_PATH}{code}").json()
        show_dates = res['data']['sessionDates']

        # Fetch shows for all the available future dates
        for show_date in show_dates:
            res = session.get(f"{BASE_URL}{SHOWS_PATH}{code}&fromdate={show_date}").json()

            shows_per_day = res['pageData']['sessions']


            for cinema in shows_per_day.values():
                for details in cinema:
                    show = {
                        'theatreId': details['cid'],
                        'startTime': datetime.strptime(details['showTime'], "%Y-%m-%dT%H:%M").isoformat(),
                        'endTime': datetime.strptime(details['closeTime'], "%Y-%m-%dT%H:%M").isoformat(),
                        'availableSeats': details['avail'],
                        'totalSeats': details['total'],
                        'screenName': details['audi'],
                        'movieId': res['meta']['movies'][0]['contentId'],
                        'language': res['meta']['movies'][0]['lang']
                    }

                    shows.append(show)

    return shows

# List of cinemas can be found using a single API call.
def fetch_cinemas(session):
    res = session.get(f"{BASE_URL}{CINEMA_PATH}").json()

    cinemas = []

    cinema_list = res['data']['cinemas']

    for item in cinema_list:
        cinema = {
            'theatreId': item['id'],
            'name': item['name'],
            'cityname': item['city'],
            'address': item['address'],
            'latitude': item['lat'],
            'longitude': item['lon']
        }

        cinemas.append(cinema)

    return cinemas

def main():
    session = get_cached_session()

    cinemas = fetch_cinemas(session)

    movie_list = fetch_movie_list(session)
    movies, codes = fetch_movies_and_codes(movie_list)

    shows = fetch_shows(session, codes)

    with (
        open("out/ticketnew-movies.csv", "w", newline="") as movies_file,
        open("out/ticketnew-sessions.csv", "w", newline="") as sessions_file,
        open("out/ticketnew-cinemas.csv", "w", newline="") as cinemas_file
    ):
        movie_writer = csv.DictWriter(
            movies_file,
            fieldnames = MOVIE_KEYS
        )

        session_writer = csv.DictWriter(
            sessions_file,
            fieldnames = SHOW_KEYS
        )

        cinema_writer = csv.DictWriter(
            cinemas_file,
            fieldnames=CINEMA_KEYS,
            extrasaction='ignore'
        )

        movie_writer.writeheader()
        session_writer.writeheader()
        cinema_writer.writeheader()

        for movie in movies:
            movie_writer.writerow(movie)

        for show in shows:
            session_writer.writerow(show)

        for cinema in cinemas:
            cinema_writer.writerow(cinema)


    print(f"[TicketNew] {len(cinemas)} cinemas")
    print(f"[TicketNew] {len(movies)} movies")

if __name__ == '__main__':
    main()