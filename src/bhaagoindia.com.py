import requests
import json

def scrape_bhaago_india(location="Bengaluru"):
	response = requests.get("https://bhaagoindia.com/search")
	data = response.json()
	blr_events_urls = [i['url'] for i in data if i['datatype'] == 'location' and i['content'] == location]
	for url in blr_events_urls:
		print(f"https://bhaagoindia.com/events/{url}")


if __name__ == "__main__":
	scrape_bhaago_india()