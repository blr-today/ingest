import json
from datetime import datetime
from curl_cffi import requests
from common.tz import IST
from bs4 import BeautifulSoup

BASE_URL = "https://www.pedalintandem.com"

def _date(date_str):
    return datetime.fromisoformat(date_str).astimezone(IST).isoformat()


def fetch_events_links(session):
	res = session.get(f"{BASE_URL}/experiences")
	soup = BeautifulSoup(res.text, 'html.parser')
	events = soup.select('div.single-experience')

	event_links = map(lambda x: x.find('a')['href'], events)

	return event_links

def fetch_events(event_links, session):
	events = []
	for event_link in event_links:
		event = []

		event_page = session.get(f"{BASE_URL}{event_link}")
		event = BeautifulSoup(event_page.text, 'html.parser')
		date_selector = event.select_one('div.product-variations-varieties select')

		# Fetch data of the events which would be happening in future otherwise skip
		if "disabled" in date_selector.attrs:
			continue

		events.append(event)

	return events

def make_event(event):
	heading = event.select_one('div.heading').get_text().strip()

	location = event.select_one('div.location').get_text().strip()

	options = {}
	options_selector = event.select_one('div.cart-details')
	opts = options_selector.select_one('div.product-variations select').select('option')
	for opt in opts:
		opt_name = opt.get_text()
		price = opt['data-price-after-discount']
		options[opt_name] = price

	dates = []
	date_opts = options_selector.select_one('div.product-variations-variety select').select('option')
	for date_opt in date_opts:
		booking_begin = str(datetime.strptime(date_opt['data-booking-begin-at'], "%Y-%m-%d %H:%M:%S %Z"))
		event_date = str(datetime.strptime(date_opt.get_text().strip(), "%d-%b-%Y"))

		dates.append({"eventDate": _date(event_date), "bookingBeginDate": _date(booking_begin)})

	duration = event.select_one('div.duration').get_text().strip()
	
	# details
	metrics = {}
	event_metrics = event.select('div.single-metric.active div.content')

	for event_metric in event_metrics:
		title = event_metric.find('p').get_text().strip()
		value = event_metric.find('h3').get_text().strip()
		metrics[title] = value

	description = event.select_one('div.trix-content div').get_text()

	return {
		"name": heading,
		"location": location,
		"options": options,
		"dates": dates,
		"duration": duration,
		"metrics": metrics,
		"description": description
	}

def main():
	session = requests.Session()
	event_links = fetch_events_links(session)
	events_data = fetch_events(event_links, session)

	events = []
	for event_data in events_data:
		event = make_event(event_data)

		events.append(event)

	with open("out/pedalintandem.json", "w") as f:
		json.dump(events, f, indent=2)

if __name__ == "__main__":
    main()
