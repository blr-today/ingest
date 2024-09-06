import json
from datetime import datetime, timedelta
from curl_cffi import requests
from common.tz import IST
from bs4 import BeautifulSoup
import re
import datefinder

BASE_URL = "https://www.pedalintandem.com"

def fetch_events_links(session):
    res = session.get(f"{BASE_URL}/experiences")
    soup = BeautifulSoup(res.text, 'html.parser')
    events = soup.select('div.single-experience')

    event_links = map(lambda x: x.find('a')['href'], events)

    return event_links

def fetch_events(event_links, session):
    events = []

    bangalore = ['bangalore', 'bengaluru', 'arkavathi', 'avalahalli', 'avathi', 'devarayanadurga',
        'gunjur', 'hennur', 'Hesaraghatta', 'kanakapura', 'malleshwaram', 'indiranagar',
        'manchanabele', 'pedal', 'pitstop',  'rajankunte']

    for event_link in event_links:

        event_page = session.get(f"{BASE_URL}{event_link}")
        event = BeautifulSoup(event_page.text, 'html.parser')
        location = event.select_one('div.location').get_text().strip().lower()

        date_selector = event.select_one('div.product-variations-varieties select')

        # Fetch data of the events which would be happening in future otherwise skip
        if ( "disabled" in date_selector.attrs):
            continue
        
        for place in bangalore:
            if place not in location:
                continue

        duration = event.select_one('div.duration').get_text().strip()
        if bool(re.search('/', duration)):
            continue

        events.append([event, event_link])

    return events

def make_event(soup):
    event = soup[0]
    url = soup[1]

    heading = event.select_one('div.heading').get_text().strip()

    location = event.select_one('div.location').get_text().strip()
    
    offers_selector = event.select_one('div.cart-details')
    offers = get_offers(offers_selector)

    duration = event.select_one('div.duration').get_text().strip()
    duration_in_hours = convert_duration_in_hours(duration)

    dates = []
    date_opts = offers_selector.select('div.product-variations-variety select[name="variety_id"] option')
    for date_opt in date_opts:
        booking_begin = datetime.strptime(date_opt['data-booking-begin-at'], "%Y-%m-%d %H:%M:%S %Z").astimezone(IST).isoformat()
        event_date = datetime.strptime(date_opt.get_text().strip(), '%d-%b-%Y')
        event_timings = find_timings(duration, event_date, event)

        # Starting time is always mentioned. So, there would be one element present in the dates
        start_date = event_timings[0].astimezone(IST).isoformat()

        # If there are two datetime in dates then it has start and end time. If not we calculate using duration
        if len(dates) == 2:
            end_date = event_timings[1].astimezone(IST)
        else:
            end_date = (datetime.fromisoformat(start_date) + timedelta(hours = duration_in_hours)).isoformat()

        dates.append({"startdate": str(start_date), "endDate": str(end_date), "availabilityStarts": str(booking_begin)})

    
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
        "offers": offers,
        "dates": dates,
        "duration": duration_in_hours,
        "description": [
        process_description(description) + "\n" + str(metrics)
        ],
        "url": BASE_URL + url,
        "keywords": url.split('/')[2]
    }

def find_timings(duration, date, soup):
    # Durations structure is `duration in hours, duration in time`. If , exists timings can be taken from here
    if ',' in duration:
        timings_str = duration.split(',')[1].lower()
        return parse_time(timings_str, date)
    
    # Checking if itinerary exists or not. If does, timings can be extracted from here.
    if soup.select_one('div.text-box div.trix-content li') != None:
        meet_data = soup.select_one('div.text-box div.trix-content li').get_text().lower()

        # Extracting timing according to the itinerary. There are two structures as followed 
        # Eg.:
        # 1. Meeting time: 6:30 am, Meeting point: ...
        # 2. Meeting time: 6:30 am, Meeting point: ...
        if 'meet at' in meet_data:
            start_time = meet_data.split('by')[1].strip()
        elif 'meeting time' in meet_data:
            start_time = re.search(r':(.*?)m', meet_data).group(0).lstrip(':').strip().lower()

        return parse_time(start_time, date)
    
    # If timings are mentioned in the description.
    meet_data = soup.select_one('div.description div.description-style div.trix-content div').get_text().strip().lower()

    # Search using time regex and remove "time:" for datefinder to work properly
    start_time = re.search(r'time:(.*?)m', meet_data).group(0).lstrip('time:').strip().lower()
    return parse_time(start_time, date)

def parse_time(timings, event_date):
    # We use datefinder coz it finds the closest year automatically
    for splitter in ["to", "-"]:
        if splitter in timings:
            timings = timings.replace(f"{splitter}", " to ")

    if bool(re.search(r'\d+\sto\s\d+\s.m', timings)):
        match = re.match(r"(\d+)\s+to\s+(\d+)\s*(am|pm)", timings)
        start_time, end_time, period = match.groups()

        timings = re.sub(re.sub(r'to\s\d+', f"to {end_time}:00", timings, 1))
        timings = re.sub(r'to\s\d+', f"to {end_time}:00", timings, 1)

    return list(datefinder.find_dates(timings, base_date=event_date))

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

def get_offers(soup):
    offers = {"priceCurrency": "INR"}
    addOn = {}

    opts = soup.select('div.product-variations select[name="variation_id"] option')
    for opt in opts:
        opt_name = opt.get_text()
        price = opt['data-price-after-discount']
        price = price.replace("\u20b9", "")
        if "rent" in opt_name or "transport" in opt_name:
            addOn[opt_name] = price
        else:
            offers[opt_name] = price

    if len(addOn) != 0:
        addOn['priceCurrency'] = 'INR'
    offers['addOn'] = addOn

    return offers

def process_description(description):
    # Remove chain of hyphen '-' and convert it into a newline
    processed_text = re.sub(r'-{2,}', '\n', description)
    processed_text = processed_text.replace("\u00a0", "\n")
    return processed_text

def main():
    session = requests.Session()
    event_links = fetch_events_links(session)
    events_data = fetch_events(event_links, session)

    events = list(map(lambda x: make_event(x), events_data))

    with open("out/pedalintandem.json", "w") as f:
        json.dump(events, f, indent=2)

if __name__ == "__main__":
    main()
