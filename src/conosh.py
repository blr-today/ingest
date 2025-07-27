import datetime
import json
import re
from bs4 import BeautifulSoup
from common.session import get_cached_session
from common.tz import IST
import dateutil.parser
import datefinder
import logging


def get_event_links():
    """Fetch event links from conosh.com physical-events page"""
    session = get_cached_session()
    response = session.get("https://conosh.com/physical-events")
    soup = BeautifulSoup(response.content, 'html.parser')
    
    address_links = soup.select('.evt_blk a')
    event_links = set()
    
    for link in address_links:
        href = link.get('href')
        if href and href != "https://conosh.com/physical-events":
            if href.startswith('/'):
                href = "https://conosh.com" + href
            event_links.add(href)
    
    return event_links


def parse_event_page(event_url):
    """Parse individual event page and return FoodEvent objects"""
    session = get_cached_session()
    response = session.get(event_url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract basic event info using CSS selectors
    title_elem = soup.select_one('h1.huge_txt')
    if not title_elem:
        logging.warning(f"No title found for event: {event_url}")
        return []
    
    title = title_elem.get_text().strip()
    # Split title by pipe and take first section only
    title = title.split('|')[0].strip()
    
    # Extract venue info from text that contains "Venue"
    venue = None
    all_text = soup.get_text()
    for line in all_text.split('\n'):
        line = line.strip()
        if 'Venue:' in line:
            venue = line.split('Venue:')[-1].strip()
            break
    
    # Set standard description
    description = f"Culinary Event organized by Conosh. See {event_url} for more details"
    
    # Extract time
    time_elem = soup.select_one('span.time')
    event_time = "7:30 PM"  # Default fallback
    if time_elem:
        event_time = time_elem.get_text().strip()
    
    # Extract image
    image_elem = soup.select_one('img.col-12.padd0')
    image_url = image_elem.get('src') if image_elem else None
    
    # Extract dates and create separate events
    events = []
    menu_items = soup.select('.menu-item-name')
    
    # Group menu items by date
    date_groups = {}
    for menu_div in menu_items:
        strong_elem = menu_div.select_one('strong')
        if not strong_elem:
            continue
            
        item_text = strong_elem.get_text().strip()
        
        # Extract date from menu item (e.g., "Aug 8th | 8-course Vegetarian Menu (1 pax)")
        date_match = re.search(r'(Aug|Sep|Oct|Nov|Dec|Jan|Feb|Mar|Apr|May|Jun|Jul)\s+(\d+)', item_text)
        if date_match:
            date_str = f"{date_match.group(1)} {date_match.group(2)}, 2025"  # Assuming 2025
            if date_str not in date_groups:
                date_groups[date_str] = []
            
            # Extract price from hidden input in the same parent container
            parent = menu_div.parent
            while parent:
                price_input = parent.select_one('input[id^="price"]')
                if price_input:
                    price = price_input.get('value')
                    offer = {
                        "@type": "Offer",
                        "name": item_text,
                        "price": price,
                        "priceCurrency": "INR"
                    }
                    date_groups[date_str].append(offer)
                    break
                parent = parent.parent
    
    # Create events for each date
    for date_str, offers in date_groups.items():
        try:
            # Use datefinder to parse the date (more robust year detection)
            date_matches = list(datefinder.find_dates(date_str))
            if not date_matches:
                logging.warning(f"Could not parse date: {date_str}")
                continue
            
            base_date = date_matches[0]
            
            # Use datefinder to parse the time with the base date
            time_matches = list(datefinder.find_dates(event_time, base_date=base_date))
            if time_matches:
                event_date = time_matches[0].replace(tzinfo=IST)
            else:
                # Fallback to combining date and time manually
                event_date = dateutil.parser.parse(f"{date_str} {event_time}").replace(tzinfo=IST)
            
            event = {
                "name": title,
                "url": event_url,
                "startDate": event_date.isoformat(),
                "description": description,
                "offers": offers
            }
            
            if image_url:
                event["image"] = image_url
            
            if venue:
                venue_parts = venue.split(',')
                event["location"] = {
                    "@type": "Place",
                    "name": venue_parts[0].strip() if venue_parts else venue,
                    "address": venue
                }
            
            events.append(event)
            
        except Exception as e:
            logging.warning(f"Failed to parse date {date_str}: {e}")
            continue
    
    return events


def main():
    """Main function to scrape conosh events"""
    events = []
    
    try:        
        # Parse each event page
        for event_url in get_event_links():
            try:
                event_data = parse_event_page(event_url)
                events.extend(event_data)
            except Exception as e:
                logging.error(f"Failed to parse event {event_url}: {e}")
                continue
        
        # Filter to future events only
        now = datetime.datetime.now(IST)
        future_events = []
        for event in events:
            try:
                event_date = dateutil.parser.parse(event['startDate'])
                if event_date >= now:
                    future_events.append(event)
            except:
                continue
        
        # Output results
        with open('out/conosh.json', 'w') as f:
            json.dump(future_events, f, indent=2)
        
        print(f"[CONOSH] {len(future_events)} events")
        
    except Exception as e:
        logging.error(f"Failed to scrape conosh events: {e}")
        return []


if __name__ == '__main__':
    main()
