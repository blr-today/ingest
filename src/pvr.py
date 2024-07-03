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
    for movie_id in get_now_showing():
        details = get_movie_details(movie_id)
        if details:
            print(f"Processing {details['title']}")
            os.makedirs(f"out/pvr/movies/{movie_id}", exist_ok=True)
            with open(f"out/pvr/movies/{movie_id}/info.json", "w") as f:
                json.dump(details, f, indent=2)

            cinemas, shows = get_movie_sessions(movie_id)
            for c in cinemas:
                all_cinemas[c["theatreId"]] = {k: c[k] for k in CINEMA_KEYS}
            with open(f"out/pvr/movies/{movie_id}/sessions.json", "w") as f:
                json.dump(shows, f, indent=2)
    with open("out/pvr/cinemas.json", "w") as f:
        json.dump(all_cinemas, f, indent=2)
