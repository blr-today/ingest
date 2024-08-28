import json
from datetime import datetime
from curl_cffi import requests
from common.tz import IST
from bs4 import BeautifulSoup

BASE_URL = "https://www.pedalintandem.com"

def _date(date_str):
    return datetime.fromisoformat(date_str).astimezone(IST).isoformat()


def fetch_events_links(session):
	res = session.get(f"{BASE_URL}/experiences", impersonate="chrome")
	soup = BeautifulSoup(res.text, 'html.parser')
	event_divs = soup.find_all('div', class_ = 'single-experience')

	# Fetch events from other pages.
	load_more = soup.find('div', class_ = 'products-loadmore')
	while load_more != None:
		url = load_more.find('a').get('href')
		
		new_page = session.get(f"{BASE_URL}{url}")
		new_page_body = BeautifulSoup(new_page.text, 'html.parser')
		
		new_events = new_page_body.find_all('div', class_ = 'single-experience')
		event_divs += new_events

		load_more = new_page_body.find('div', class_ = 'products-loadmore')

	event_links = []
	for event_div in event_divs:
		url = event_div.find('a').get('href')
		event_links.append(url)

	return event_links

def fetch_events(event_links, session):
	events = []
	for event_link in event_links:
		event = []

		event_page = session.get(f"{BASE_URL}{event_link}", impersonate='chrome')
		event = BeautifulSoup(event_page.text, 'html.parser')
		date_selector = event.find('div', 'product-variations-varieties').find('select')

		# Fetch data of the events which would be happening in future otherwise skip
		if "disabled" in date_selector.attrs:
			continue

		events.append(event)

	return events

def make_event(event):
	heading = event.find('div', class_ = 'heading').get_text().strip()

	location = event.find('div', class_ = 'location').get_text().strip()

	options = []
	options_selector = event.find('div', class_ = 'cart-details')
	opts = options_selector.find('div', class_ = 'product-variations').find('select').find_all('option')
	for opt in opts:
		opt_name = opt.get_text()
		price = opt['data-price-after-discount']
		options.append({opt_name: price})

	dates = []
	date_opts = options_selector.find('div', class_ = 'product-variations-variety').find('select').find_all('option')
	for date_opt in date_opts:
		booking_begin = str(datetime.strptime(date_opt['data-booking-begin-at'], "%Y-%m-%d %H:%M:%S %Z"))
		event_date = str(datetime.strptime(date_opt.get_text().strip(), "%d-%b-%Y"))

		dates.append({"eventDate": _date(event_date), "bookingBeginDate": _date(booking_begin)})

	duration = event.find('div', class_ = 'duration').get_text().strip()
	
	# details
	metrics = []
	event_metrics = event.find_all('div', class_ = 'single-metric active')
	for event_metric in event_metrics:
		metric = event_metric.find('div', class_ = 'content') 
		title = metric.find('p').get_text().strip()
		value = metric.find('h3').get_text().strip()
		metrics.append({title: value})

	description = event.find('div', class_ = 'trix-content').find('div').get_text()

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
