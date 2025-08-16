"""
PuttingScene Event Scraper

This module scrapes event data from puttingscene.com and converts it to Schema.org Event format.
The scraper uses binary search to find the latest event ID and fetches recent events.
"""

import json
import html
import urllib.parse
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from common.session import get_cached_session
from common.tz import IST
from bs4 import BeautifulSoup
import re
import cleanurl

# Configuration constants
BASE_EVENT_ID = 520
EVENTS_PER_DAY = 10
BASE_DATE = datetime(2025, 8, 3).date()
RECENT_EVENTS_COUNT = 99
DEFAULT_EVENT_DURATION_HOURS = 2

logger = logging.getLogger("PUTTINGSCENE")

# Configure logging if not already configured
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='[%(name)s] - %(levelname)s - %(message)s'
    )


def _clean_instagram_url(url: str) -> str:
    """Remove Instagram-specific tracking parameters."""
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    if 'igsh' in query_params:
        del query_params['igsh']
    new_query = urllib.parse.urlencode(query_params, doseq=True)
    return urllib.parse.urlunparse((
        parsed.scheme, parsed.netloc, parsed.path,
        parsed.params, new_query, parsed.fragment
    ))


def find_max_event_id() -> int:
    """
    Find the highest event ID using delta-based search around the starting guess.
    
    Uses powers of 2 deltas starting from 16, then refines by doubling/halving
    the delta based on whether we need to go up or down.
    
    Returns:
        The highest valid event ID found
    """
    session = get_cached_session(allowable_methods=["HEAD"], days=7)
    
    # Calculate starting guess based on days since base date
    today = datetime.now().date()
    days_diff = (today - BASE_DATE).days
    start_guess = BASE_EVENT_ID + (days_diff * EVENTS_PER_DAY)
    
    logger.debug(f"Starting delta search from event ID {start_guess}")
    
    def check_event_exists(event_id: int) -> bool:
        """Check if an event ID exists (returns 200)."""
        try:
            response = session.head(f"https://puttingscene.com/events/{event_id}", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Error checking event {event_id}: {e}")
            return False
    
    # Check if our starting guess exists
    current = start_guess
    if not check_event_exists(current):
        logger.debug(f"Starting guess {current} doesn't exist, searching backwards")
        # Search backwards first
        delta = 16
        while delta <= 512:  # Max reasonable backwards search
            test_id = current - delta
            if test_id <= 0:
                break
            if check_event_exists(test_id):
                current = test_id
                logger.debug(f"Found valid event at {current} (delta -{delta})")
                break
            delta *= 2
        else:
            logger.warning(f"Could not find valid events near {start_guess}")
            return start_guess
    
    # Now find the highest valid event ID starting from current
    logger.debug(f"Searching forward from {current}")
    max_found = current
    delta = 16
    
    # First, find the direction and rough boundary
    while delta <= 512:  # Reasonable upper limit
        test_id = current + delta
        logger.debug(f"Testing event {test_id} (delta +{delta})")
        
        if check_event_exists(test_id):
            max_found = test_id
            logger.debug(f"Found valid event at {test_id} (delta +{delta})")
            delta *= 2  # Double delta to search further
        else:
            logger.debug(f"Event {test_id} doesn't exist, refining search")
            break
    
    # Now refine between max_found and max_found + delta
    logger.debug(f"Refining search between {max_found} and {max_found + delta}")
    
    # Binary search in the narrowed range
    low = max_found
    high = max_found + delta
    
    while low < high - 1:
        mid = (low + high) // 2
        logger.debug(f"Binary search testing {mid}")
        
        if check_event_exists(mid):
            low = mid
            logger.debug(f"Event {mid} exists, updating low bound")
        else:
            high = mid
            logger.debug(f"Event {mid} doesn't exist, updating high bound")
    
    logger.info(f"Found max event ID: {low}")
    return low


def fetch_event_html(event_id):
    session = get_cached_session()
    response = session.get(f"https://puttingscene.com/events/{event_id}")
    if response.status_code == 200:
        return response.text
    return None


def parse_event_html(html_content, event_id):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract title
    title_elem = soup.find('h1')
    if not title_elem:
        return None
    title = html.unescape(title_elem.get_text().strip())
    
    # Skip test events
    if 'test' in title.lower():
        return None
    
    # Extract description
    about_section = soup.find('h2', string='About the Experience')
    description = ""
    if about_section and about_section.find_next('p'):
        description = html.unescape(about_section.find_next('p').get_text().strip())
    
    # Extract image
    og_image = soup.find('meta', property='og:image')
    image = og_image['content'] if og_image else ""
    
    # Extract date and time
    date_span = soup.find('span', class_='font-bold text-[13px] text-black')
    time_span = soup.find('span', class_='text-[13px] text-black')
    
    if not date_span or not time_span:
        return None
    
    date_text = date_span.get_text().strip()
    time_text = time_span.get_text().strip()
    
    # Parse date (format: "Sun, 3 Aug")
    try:
        current_date = datetime.now()
        current_year = current_date.year
        
        # Try current year first
        date_obj = datetime.strptime(f"{date_text} {current_year}", "%a, %d %b %Y")
        
        # If the parsed date is more than 6 months in the past, try next year
        if (current_date - date_obj).days > 180:
            date_obj = datetime.strptime(f"{date_text} {current_year + 1}", "%a, %d %b %Y")
        
        # Only include future events
        if date_obj < datetime.now():
            return None

        time_obj = datetime.strptime(time_text, "%I:%M %p").time()
        date_obj = date_obj.replace(hour=time_obj.hour).replace(minute=time_obj.minute).replace(tzinfo=IST)
            
        # Add IST timezone
        start_date = date_obj.isoformat()
        end_date = (date_obj + timedelta(hours=2)).isoformat()
        
    except ValueError:
        return None
    
    # Extract location - look for map pin icon and associated text
    location_name = ""
    location_url = ""
    
    # Find map pin icon and get the text from the same container
    map_icons = soup.find_all('svg', class_='lucide lucide-map-pin')
    for icon in map_icons:
        # Find the parent <a> tag
        parent_a = icon.find_parent('a')
        if parent_a and parent_a.get('href'):
            # Get the location name from the span next to the icon
            location_span = parent_a.find('span', class_='font-bold text-[13px] text-black')
            if location_span:
                location_name = location_span.get_text().strip()
                href = parent_a['href']
                # Clean Google Maps URLs
                if 'google.com/maps' in href or 'maps.app.goo.gl' in href:
                    clean_result = cleanurl.cleanurl(href, respect_semantics=True)
                    location_url = clean_result.url if clean_result else href
                break
    
    # Extract pricing and availability information from bottom booking section
    price = ""
    availability_status = ""
    remaining_capacity = None
    
    # Look for the bottom booking section with pricing (try multiple selectors)
    bottom_section = soup.find('div', class_=lambda x: x and 'fixed' in x and 'bottom-0' in x) or \
                     soup.find('div', class_='fixed bottom-0') or \
                     soup.find('div', {'class': re.compile(r'.*fixed.*bottom.*')})
                     
    if bottom_section:
        # Look for availability information (e.g., "10 SLOTS LEFT")
        availability_elem = bottom_section.find('span', string=re.compile(r'\d+\s+SLOTS?\s+LEFT', re.IGNORECASE))
        if availability_elem:
            availability_status = "InStock"
            # Extract remaining capacity
            slots_text = availability_elem.get_text().strip()
            slots_match = re.search(r'(\d+)\s+SLOTS?\s+LEFT', slots_text, re.IGNORECASE)
            if slots_match:
                remaining_capacity = int(slots_match.group(1))
    
    # Extract booking URL (look for "Book Now" span in button)
    book_span = soup.find('span', string='Book Now')
    booking_url = ""
    if book_span:
        bottom_div = book_span.find_parent('div')
        # find all spans inside bottom_div
        for span in bottom_div.find_all('span'):
            price_text= span.get_text()
            if '₹' in price_text:
                price_match = re.search(r'₹\s*([\d,]+\.?\d*)', price_text)
                if price_match:
                    price = price_match.group(1).replace(',', '')
            if 'Free' in price_text:
                price = "0"
        # Find the ancestor <a> tag
        parent_a = book_span.find_parent('a')
        if parent_a and parent_a.get('href'):
            href = parent_a['href']
            # Only use external URLs, not puttingscene.com or maps URLs
            if not href.startswith('/') and 'puttingscene.com' not in href and 'maps.app.goo.gl' not in href:
                # Clean URL to remove UTM parameters
                clean_result = cleanurl.cleanurl(href, respect_semantics=True)
                booking_url = clean_result.url if clean_result else href
                
                # Additional manual cleaning for Instagram igsh parameter
                if 'instagram.com' in booking_url and 'igsh=' in booking_url:
                    booking_url = _clean_instagram_url(booking_url)
    
    event = {
        "@type": "Event",
        "name": title,
        "url": f"https://puttingscene.com/events/{event_id}",
        "startDate": start_date,
        "endDate": end_date,
        "description": description,
        "image": image,
        "location": {
            "name": location_name,
            "address": f"{location_name}, Bangalore"
        }
    }
    
    if location_url:
        event["location"]["url"] = location_url
    
    if booking_url:
        event["sameAs"] = booking_url
    
    # Add offer information if price is available
    if price != "0":
        offer = {
            "@type": "Offer",
            "price": price,
            "priceCurrency": "INR"
        }
        
        # Add availability information if present
        if availability_status:
            offer["availability"] = f"http://schema.org/{availability_status}"
        
        # Add remaining capacity if available
        if remaining_capacity is not None:
            offer["remainingAttendeeCapacity"] = remaining_capacity
        
        event["offers"] = [offer]
    if price == "0":
        event["isAccessibleForFree"] = True
    
    return event


def fetch_putting_scenes():
    max_event_id = find_max_event_id()
    events = []
    
    # Fetch recent events
    start_id = max(1, max_event_id - RECENT_EVENTS_COUNT)
    html_content = None
    for event_id in range(start_id, max_event_id + 1):
        res = fetch_event_html(event_id)
        if html_content == None and res == None:
            break
        elif res:
            event = parse_event_html(res, event_id)
            if event:
                events.append(event)
        html_content = res
    
    # Sort events by URL to ensure consistent output order
    return sorted(events, key=lambda x: x["url"])


# Write to puttingscene.json
if __name__ == "__main__":
    with open("out/puttingscene.json", "w") as f:
        events = fetch_putting_scenes()
        json.dump(events, f, indent=2)
        print(f"[PUTTINGSCENE] {len(events)} events")
