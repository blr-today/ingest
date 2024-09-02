import json
from datetime import datetime, timedelta
from curl_cffi import requests
from common.tz import IST
from bs4 import BeautifulSoup
import re

BASE_URL = "https://www.pedalintandem.com"

def fetch_events_links(session):
	res = session.get(f"{BASE_URL}/experiences")
	soup = BeautifulSoup(res.text, 'html.parser')
	events = soup.select('div.single-experience')

	event_links = map(lambda x: x.find('a')['href'], events)

	return event_links

def fetch_events(event_links, session):
	events = []
	for event_link in event_links:

		event_page = session.get(f"{BASE_URL}{event_link}")
		event = BeautifulSoup(event_page.text, 'html.parser')
		location = event.select_one('div.location').get_text().strip()

		date_selector = event.select_one('div.product-variations-varieties select')

		# Fetch data of the events which would be happening in future otherwise skip
		if ( "disabled" in date_selector.attrs):
			continue
		
		if not ( bool(re.search('bangalore', location, re.IGNORECASE)) or
			bool(re.search('bengaluru', location, re.IGNORECASE)) or
			bool(re.search('arkavathi', location, re.IGNORECASE)) or
			bool(re.search('avalahalli', location, re.IGNORECASE)) or
			bool(re.search('avathi', location, re.IGNORECASE)) or
			bool(re.search('devarayanadurga', location, re.IGNORECASE)) or
			bool(re.search('gunjur', location, re.IGNORECASE)) or
			bool(re.search('hennur', location, re.IGNORECASE)) or
			bool(re.search('Hesaraghatta', location, re.IGNORECASE)) or
			bool(re.search('kanakapura', location, re.IGNORECASE)) or
			bool(re.search('malleshwaram', location, re.IGNORECASE)) or
			bool(re.search('indiranagar', location, re.IGNORECASE)) or
			bool(re.search('manchanabele', location, re.IGNORECASE)) or
			bool(re.search('pedal', location, re.IGNORECASE)) or
			bool(re.search('pitstop', location, re.IGNORECASE)) or 
			bool(re.search('rajankunte', location, re.IGNORECASE)) ):
			continue

		duration = event.select_one('div.duration').get_text().strip()
		if bool(re.search('/', duration)):
			continue

		events.append(event)

	return events

def make_event(event):
	heading = event.select_one('div.heading').get_text().strip()

	location = event.select_one('div.location').get_text().strip()

	offers = {}
	addOn = {}
	offers_selector = event.select_one('div.cart-details')
	opts = offers_selector.select('div.product-variations select[name="variation_id"] option')
	for opt in opts:
		opt_name = opt.get_text()
		price = opt['data-price-after-discount']
		price = price.replace("\u20b9", "")
		if "rent" in opt_name or "transport" in opt_name:
			addOn[opt_name] = price
		else:
			offers[opt_name] = price
	offers['addOn'] = addOn

	duration = event.select_one('div.duration').get_text().strip()
	duration_in_hours = convert_duration_in_hours(duration)

	# Find the starting time
	if ',' in duration:
		# If there is comma then the duration contains start time and end time
		timing = duration.split(',')[1].lower()

		# Check if time has pm time. Extra is used to convert the time two 24 hour format
		if 'pm' in timing:
			extra = 12
		else:
			extra = 0

		if 'to' in timing:
			start_time = timing.split('to')[0].strip().lower()
		else:
			start_time = timing.split('-')[0].strip().lower()

	elif event.select_one('div.text-box div.trix-content li') != None:
		meet_data = event.select_one('div.text-box div.trix-content li').get_text().lower()
		if 'meet at' in meet_data:
			start_time = meet_data.split('by')[1].strip()
		elif 'meeting time' in meet_data:
			start_time = re.search(r':(.*?),?', meet_data).group(0).lstrip(':').strip().lower()
	else:
		meet_data = event.select_one('div.description div.description-style div.trix-content div').get_text().strip().lower()
		start_time = re.search(r'')


	dates = []
	date_opts = offers_selector.select('div.product-variations-variety select[name="variety_id"] option')
	for date_opt in date_opts:
		booking_begin = datetime.strptime(date_opt['data-booking-begin-at'], "%Y-%m-%d %H:%M:%S %Z").astimezone(IST).isoformat()
		startdate = datetime.strptime(date_opt.get_text().strip(), "%d-%b-%Y").astimezone(IST).isoformat()
		endDate = (datetime.fromisoformat(startdate) + timedelta(hours = duration_in_hours)).isoformat()

		dates.append({"startdate": startdate, "endDate": endDate, "availabilityStarts": booking_begin})
	
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
		"priceCurrency": "INR",
		"offers": offers,
		"dates": dates,
		"duration": duration_in_hours,
		"description": [
		process_description(description),
		metrics
		]
	}

def convert_to_24_hour(start_time):
    # Extract the numeric part of the time
    time_match = re.search(r'[0-9]+(:[0-9]+)?', start_time)
    
    if time_match:
        time_str = time_match.group(0)
        # Split hours and minutes
        if ':' in time_str:
            hours, minutes = map(int, time_str.split(':'))
        else:
            hours = int(time_str)
            minutes = 0

        # Check for 'am' or 'pm' and adjust hours accordingly
        if 'am' in start_time.lower():
            if hours == 12:  # Special case for 12 am
                hours = 0
        elif 'pm' in start_time.lower():
            if hours != 12:  # Special case for 12 pm
                hours += 12

        # Convert time to decimal format
        total_hours = hours + minutes / 60.0
        return total_hours

def convert_duration_in_hours(duration):
	duration_range = duration.split(',')[0]

	# fetch the upper limit of time duration
	if bool(re.search("hour", duration)):
		if bool(re.search('to', duration_range)):
			duration_in_hours = duration_range.replace("hours", "").split('to')[1].strip()
		elif bool(re.search('-', duration_range)):
			duration_in_hours = duration_range.replace("hours", "").split('-')[1].strip()
		else:
			duration_in_hours = duration_range.replace("hours", "").strip()

	elif bool(re.search("hrs", duration)):
		if bool(re.search('to', duration_range)):
			duration_in_hours = duration_range.replace("hrs", "").split('to')[1].strip()
		elif bool(re.search('-', duration_range)):
			duration_in_hours = duration_range.replace("hrs", "").split('-')[1].strip()
		else:
			duration_in_hours = duration_range.replace("hrs", "").strip()

	else:
		duration_in_hours = 0

	return int(duration_in_hours)

def process_description(description):
	# Remove chain of hyphen '-' and convert it into a newline
	processed_text = re.sub(r'-{2,}', '\n', description)
	processed_text = processed_text.replace("\u00a0", "\n")
	return processed_text

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
