import http.client
import json


def get_events(page=1):
    conn = http.client.HTTPSConnection("www.skillboxes.com")
    payload = {
        "page": page,
        "city": 9,
    }

    headers = {"Content-Type": "application/json"}

    conn.request(
        "POST", "/servers/v1/api/event-new/get-event", json.dumps(payload), headers
    )

    res = json.loads(conn.getresponse().read().decode("utf-8"))
    for item in res["items"]:
        yield f"https://www.skillboxes.com/events/{item['slug']}"
    if res["next"]:
        yield from get_events(page + 1)
    conn.close()


def __main__():
    for url in get_events():
        print(url)


if __name__ == "__main__":
    __main__()
