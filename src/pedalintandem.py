import json
from datetime import datetime, timedelta
from curl_cffi import requests
from common.tz import IST
from bs4 import BeautifulSoup
import re
import datefinder

BASE_URL = "https://www.pedalintandem.com"
BLR_LOCATIONS = [
    'bangalore', 'bengaluru', 'arkavathi', 'avalahalli', 
    'avathi', 'devarayanadurga', 'gunjur', 'hennur',
    'Hesaraghatta', 'kanakapura', 'malleshwaram',
    'indiranagar', 'manchanabele', 'pedal', 'pitstop',
    'rajankunte', 'nandi', 'melagiri'
]

def fetch_events_links(session):
    res = session.get(f"{BASE_URL}/experiences")
    soup = BeautifulSoup(res.text, 'html.parser')
    events = soup.select('div.single-experience')

    return map(lambda x: x.find('a')['href'], events)

def fetch_events(event_links, session):
    events = []

    for event_link in event_links:
        url = f"{BASE_URL}{event_link}"
        event_page = session.get(url)
        event = BeautifulSoup(event_page.text, 'html.parser')
        location = event.select_one('div.location').get_text().strip().lower()

        date_selector = event.select_one('div.product-variations-varieties select')

        # Fetch data of the events which would be happening in future otherwise skip
        if ( "disabled" in date_selector.attrs):
            continue
        
        
        # Select only single day event. Multi day events are in the format "2D/ 3N"
        duration = event.select_one('div.duration').get_text().strip()
        if bool(re.search('/', duration)):
            print(f"[PIT] {event_link} is {duration} long, assuming MULTIDAY and ignoring")
            continue

        # Skip if location is not in bangalore
        inside_blr = False
        for place_inside_blr in BLR_LOCATIONS:
            if place_inside_blr in location.lower():
                inside_blr = True

        if not inside_blr:
            print(f"[PIT] {event_link} {location} not in BLR")
            continue

        # Pass url so that it can be added in event
        events.append([event, event_link])

    return events

def make_event(soup):
    event = soup[0]
    url = soup[1]

    heading = event.select_one('div.heading').get_text().strip()

    location = find_location(event)

    offers_selector = event.select_one('div.cart-details')

    duration = event.select_one('div.duration').get_text().strip()
    duration_in_hours = convert_duration_in_hours(duration)

    date_opts = offers_selector.select('div.product-variations-variety select[name="variety_id"] option')
    for date_opt in date_opts:
        booking_begin = datetime.strptime(date_opt['data-booking-begin-at'], "%Y-%m-%d %H:%M:%S %Z").astimezone(IST).isoformat()
        event_date = datetime.strptime(date_opt.get_text().strip(), '%d-%b-%Y')
        event_timings = find_timings(duration, event_date, event)

        # Starting time is always mentioned. So, there would be one element present in the dates
        start_date = event_timings[0].astimezone(IST).isoformat()

        # If there are two datetime in dates then it has start and end time. If not we calculate using duration
        if len(event_timings) == 2:
            end_date = event_timings[1].astimezone(IST).isoformat()
        else:
            end_date = (datetime.fromisoformat(start_date) + timedelta(hours = duration_in_hours)).isoformat()

    # Fetch duration from timings if the duration_in_hours is set to 0
    if duration_in_hours == 0:
        duration_in_hours = datetime.fromisoformat(end_date).hour - datetime.fromisoformat(start_date).hour

    offers = get_offers(offers_selector, booking_begin)
    
    # details
    metrics = {}
    event_metrics = event.select('div.single-metric.active div.content')

    for event_metric in event_metrics:
        title = event_metric.find('p').get_text().strip()
        value = event_metric.find('h3').get_text().strip()
        metrics[title] = value

    description = event.select_one('div.trix-content div').get_text()

    return {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": heading,
        "sports": "Cycling",
        "location": location,
        "offers": offers,
        "startDate": start_date,
        "endDate": end_date,
        "description": process_description(description) + "\n" + str(metrics),
        "url": BASE_URL + url,
        "keywords": [url.split('/')[2], "PEDALINTANDEM"]
    }

def find_location(soup):
    location = {
        "@type": "Place"
    }
    address = None

    SELECTORS = [
        ('div.text-box div.trix-content li', [
            r'meet\s+at\s+([^,]+),',
            r'meeting\s+point(?:[^:]*?):\s+([^.]+)(?:\.|\n|$)'
        ]),
        ('div.description div.description-style div.trix-content div', [
            r'location(?:[^:]*?):\s+([^.]+)(?:\.|\n|$)'
        ]),
        ('div.location', [
            r'(.*)'
        ])
    ]

    address = None
    for css_selector, regex_patterns in SELECTORS:
        element = soup.select_one(css_selector)
        if not element:
            continue
            
        text = element.get_text().lower().strip()
        
        for pattern in regex_patterns:
            matches = re.search(pattern, text)
            if matches:
                address = matches.group(1).strip()
                break
        
        if address:
            break

    if address.lower() == 'pedal in tandem' or 'indiranagar' in address.lower():
        location['address'] = '837/1, 2nd Cross, 7th Main, 2nd Stage, Indiranagar, Bengaluru, Karnataka'
        location['name'] = 'Pedal in Tandem'
    else:
        location['address'] = address
    return location

def find_timings(duration, date, soup):
    """
    Extract timing information from various sources in the soup.
    
    Args:
        duration: String containing possible duration and time information
        date: Date to associate with the extracted time
        soup: BeautifulSoup object containing the HTML
    
    Returns:
        Parsed time from parse_time function
    """
    # Check if timing is in the duration string
    if ',' in duration:
        timings_str = duration.split(',')[1].strip().lower()
        possible_time = parse_time(timings_str, date)
        if len(possible_time) > 0:
            return possible_time
    
    # Define sources to check for timing information
    timing_sources = [
        # Source 1: Check itinerary in text-box
        {
            'selector': 'div.text-box div.trix-content li',
            'patterns': [
                # "Meet at X, by 3 pm" pattern
                (r'by\s+([^\.,]+(?:am|pm|AM|PM))', 'meet at'),
                # "Meeting time: 6:30 am" pattern
                (r'meeting\s+time:?\s+([^\.,]+(?:am|pm|AM|PM))', None)
            ]
        },
        # Source 2: Check description
        {
            'selector': 'div.description div.description-style div.trix-content div',
            'patterns': [
                # "time: 8:30 am" pattern
                (r'time:?\s+([^\.,]+(?:am|pm|AM|PM))', None)
            ]
        }
    ]
    
    # Check each source for timing information
    for source in timing_sources:
        for element in soup.select(source['selector']):
            text = element.get_text().strip().lower()
            
            for pattern, flag in source['patterns']:
                # If flag is None or the flag text is in the content
                if flag is None or flag in text:
                    matches = re.search(pattern, text)
                    if matches:
                        return parse_time(matches.group(1), date)
    
    # If no timing was found, raise an exception
    raise ValueError("Could not find timing information in any of the expected locations")

def parse_time(timings, event_date):
    # We pass event date to get the correct date time of event
    for splitter in ["to", "-"]:
        if splitter in timings:
            timings = timings.replace(f"{splitter}", " to ")

    # Convert the timings from "hh to hh pm" to "hh:mm to hh:mm pm" format for datefinder to work properly.
    if bool(re.search(r'\d+\s+to\s+\d+[\s]*.m', timings)):
        match = re.match(r"(\d+)\s+to\s+(\d+)[\s]*(am|pm)", timings)
        start_time, end_time, period = match.groups()

        timings = re.sub(r'\d+\s+to', f"{start_time}:00 to", timings, count=1)
        timings = re.sub(r'to\s+\d+', f"to {end_time}:00", timings, count=1)

    # Convert to "hh:mm pm to hh:mm pm". Otherwise it takes first time as am
    if 'am' not in timings and timings.count('pm') == 1:
        timings = timings.replace('to', 'pm to')

    return list(datefinder.find_dates(timings, base_date=event_date))

def convert_duration_in_hours(duration):
    duration_range = duration.split(',')[0]

    # Duration either has a range or fixed no. of hours.
    for hour in ["hours", "hrs"]:
        if hour in duration_range:
            duration_range = duration_range.replace(hour, "")

            for splitter in ["to", "-"]:
                if splitter in duration_range:
                    return int(duration_range.split(splitter)[1].strip())
            
            return int(duration_range.strip())

    return 0

def get_offers(soup, availability_starts):
    offers = [] 
    addOns = [] 

    opts = soup.select('div.product-variations select[name="variation_id"] option')
    for opt in opts:
        offer = {"priceCurrency": "INR", '@type': 'offer'}
        opt_name = opt.get_text().lower()
        price = opt['data-price-after-discount']
        price = price.replace("\u20b9", "").replace(",", "")
        if "rent" in opt_name or "transport" in opt_name:
            addOn = {'@type': 'offer'}
            addOn['name'] = opt_name
            addOn['price'] = price
            addOn['priceCurrency'] = "INR"
            addOns.append(addOn)
        else:
            offer['name'] = opt_name
            offer['price'] = price
            offer['availabilityStarts'] = availability_starts
            offers.append(offer)

    if len(addOns) != 0:
        offers.append(addOns)

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
