import csv
import requests
import os
import json
from datetime import datetime
from common.session import get_cached_session

BASE_URL = "https://api3.pvrcinemas.com/api/v1/booking/content"
CITY = "Bengaluru"
HEADERS = {
    "city": CITY,
    "appVersion": "18.2",
    "platform": "ANDROID",
    "authorization": "Bearer",
}

MOVIE_KEYS = [
    "title",
    "imdb_url",
    "adult",
    "overview",
    "runtime",
    "status",
    "tagline",
    "facebook",
    "instagram",
    "twitter",
    "tmdb_id",
]

CINEMA_KEYS = [
    "theatreId",
    "name",
    "cityName",
    "address1",
    "address2",
    "address3",
    "latitude",
    "longitude",
    "telephone",
    "fbDeliveryOnSeat",
    "caretakerContactNo",
    "foodAvailable",
    "handicapRamp",
    "handicap",
    "miv",
]

SHOW_KEYS = [
    "totalSeats",
    "availableSeats",
    "screenName",
    "language",
    "movieFormat",
    "subtitle",
    "screenType",
    "filmFormat",
]


def get_now_showing():
    url = f"{BASE_URL}/nowshowing"
    payload = {"city": CITY}
    response = requests.post(url, json=payload, headers=HEADERS)

    for x in response.json()["output"]["mv"]:
        yield x["id"]


def get_movie_sessions(movie_id):
    session = get_cached_session(allowable_methods=["GET", "POST"])
    url = f"{BASE_URL}/msessions"

    payload = {"mid": movie_id}

    response = session.post(url, json=payload, headers=HEADERS)
    try:
        d = response.json()["output"]["movieCinemaSessions"]
    except:
        print("Failed to parse")
        print(response.text)
        return ([], [])
    cinemas = [x["cinema"] for x in d]
    shows = []
    for x in d:
        theaterId = x["cinema"]["theatreId"]
        for y in x["experienceSessions"]:
            experienceKey = y["experienceKey"]
            for z in y["shows"]:
                shows.append(
                    {k: z[k] for k in SHOW_KEYS}
                    | {
                        "theatreId": theaterId,
                        "experienceKey": experienceKey,
                        "startTime": datetime.fromtimestamp(
                            z["showTimeStamp"] / 1000
                        ).isoformat(),
                        "endTime": datetime.fromtimestamp(
                            z["endTimeStamp"] / 1000
                        ).isoformat(),
                    }
                )

    return (cinemas, shows)


def get_movie_details(movie_id):
    url = f"{BASE_URL}/movie"

    payload = {"mid": movie_id}

    session = get_cached_session(days=15, allowable_methods=["GET", "POST"])

    response = session.post(url, json=payload, headers=HEADERS)
    try:
        output = response.json()["output"]
        data = output["tmdb"]
    except:
        print(response.text)
        return None
    try:
        return {
            "title": output["movie"]["filmName"],
            "imdb_url": data["imdb_id"] if "imdb_id" in data else None,
            "adult": data["adult"],
            "overview": data["overview"],
            "runtime": data["runtime"] if data["runtime"] > 0 else None,
            "status": data["status"],
            "tagline": data["tagline"],
            "facebook": data["facebook"],
            "instagram": data["instagram"],
            "twitter": data["twitter"],
            "tmdb_id": str(data["cast"][0]["mid"]),
        }
    except:
        return None


if __name__ == "__main__":
    all_cinemas = dict()

    # Ensure output directory exists
    os.makedirs("out/pvr", exist_ok=True)

    # Open CSV files for writing
    with (
        open("out/pvr-movies.csv", "w", newline="") as movies_file,
        open("out/pvr-sessions.csv", "w", newline="") as sessions_file,
        open("out/pvr-cinemas.csv", "w", newline="") as cinemas_file,
    ):
        movie_writer = csv.DictWriter(movies_file, fieldnames=["movieId"] + MOVIE_KEYS)
        session_writer = csv.DictWriter(
            sessions_file,
            fieldnames=["movieId"]
            + SHOW_KEYS
            + ["theatreId", "experienceKey", "startTime", "endTime"],
        )

        cinema_writer = csv.DictWriter(
            cinemas_file, fieldnames=CINEMA_KEYS, extrasaction="ignore"
        )

        # Write headers
        movie_writer.writeheader()
        session_writer.writeheader()
        cinema_writer.writeheader()

        movie_counter = 0
        for movie_id in get_now_showing():
            movie_counter += 1
            details = get_movie_details(movie_id)
            if details:
                # Write movie details to CSV
                movie_info = {**details, "movieId": movie_id}
                movie_writer.writerow(movie_info)

                cinemas, shows = get_movie_sessions(movie_id)
                for c in cinemas:
                    if c["theatreId"] not in all_cinemas:
                        all_cinemas[c["theatreId"]] = c
                for show in shows:
                    show["movieId"] = movie_id
                    session_writer.writerow(show)

        cinema_writer.writerows(
            sorted(all_cinemas.values(), key=lambda x: x["theatreId"])
        )

    print(f"[PVR] {len(all_cinemas)} cinemas")
    print(f"[PVR] {movie_counter} movies")
