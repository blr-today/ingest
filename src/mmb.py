from common.session import get_cached_session
import json
import datetime


def fetch_events():
    session = get_cached_session()
    payload = {
        "langId": "1",
        "filterData": json.dumps(
            {
                "adress_IDtxt": "Bangalore",
                "dateStart": datetime.datetime.now().strftime("%Y-%m-%d 00:00:00"),
                "dateEnd": (
                    datetime.datetime.now() + datetime.timedelta(days=30)
                ).strftime("%Y-%m-%d 23:59:59"),
            }
        ),
    }

    response = session.post(
        "https://www.goethe.de/rest/objeventcalendarv3/events/fetchEvents", data=payload
    )
    for event in response.json()["eventItems"]:
        print(f"https://www.goethe.de/ins/in/en/ver.cfm?event_id={event['object_id']}")


if __name__ == "__main__":
    fetch_events()
