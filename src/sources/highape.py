import requests
import json

HEADERS = {
    "Accept-Encoding": "gzip"
}

def scrape_highape(location):
    base_url = "https://www.highape.com/desktop/api/bangalore/pages/1/sections/3"
    params = {"search": "", "page": 1}
    response = requests.get(base_url, params=params, headers=HEADERS)
    data = response.json()

    for event in data['events']:
        yield f"https://www.highape.com/bangalore/events/{event['permalink']}"


# Example usage:
location = "bangalore"
for url in scrape_highape(location):
    print(url)
