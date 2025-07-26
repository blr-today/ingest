import json
import logging
import os
from datetime import datetime, date
from bs4 import BeautifulSoup
from common.session import get_cached_session
from common.tz import IST

EVENTS_URL = "https://www.sabhablr.in/events"
EVENT_DETAIL_URL_PREFIX = "https://www.sabhablr.in/event-details/"

log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)


def extract_text_from_rich_content(nodes):
    """Convert rich text content to plain text"""
    if not nodes:
        return ""
    
    text_parts = []
    for node in nodes:
        if node.get("type") == "PARAGRAPH" and "nodes" in node:
            for child_node in node["nodes"]:
                if child_node.get("type") == "TEXT" and "textData" in child_node:
                    text_parts.append(child_node["textData"]["text"])
        elif node.get("type") == "TEXT" and "textData" in node:
            text_parts.append(node["textData"]["text"])
    
    return " ".join(text_parts).strip()


def parse_datetime(date_str, timezone=IST):
    """Parse ISO datetime string to timezone-aware datetime"""
    dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    return dt.astimezone(timezone).isoformat()


def fetch_event_detail(slug, session):
    """Fetch event detail page and extract long description"""
    try:
        url = f"{EVENT_DETAIL_URL_PREFIX}{slug}"
        response = session.get(url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        script_tag = soup.find("script", {"type": "application/json", "id": "wix-warmup-data"})
        
        if not script_tag:
            return None
            
        data = json.loads(script_tag.string)
        event_data = data["appsWarmupData"]["140603ad-af8d-84a5-2c80-a0f60cb47351"]["EventsPageInitialState"]["event"]["event"]
        
        if "longDescription" in event_data:
            nodes = event_data["longDescription"].get("nodes", [])
            return extract_text_from_rich_content(nodes)
            
    except (KeyError, TypeError, Exception):
        pass
        
    return None


def transform_event(event, session):
    """Transform raw event data to schema.org format"""
    try:
        # Check for critical attributes - drop event if missing
        if not event.get("title") or not event.get("slug"):
            logger.warning(f"Dropping event missing title or slug: {event}")
            return None
            
        name = event["title"]
        slug = event["slug"]
        description = event.get("description")
        
        # Check date - only include future events
        scheduling = event.get("scheduling", {}).get("config", {})
        if "startDate" in scheduling:
            start_date = datetime.fromisoformat(scheduling["startDate"].replace('Z', '+00:00'))
            event_date = start_date.date()
            today = date.today()
            
            if event_date < today:
                logger.info(f"Skipping past event: {name} ({event_date})")
                return None
        
        # Check if it's an external event
        is_external = "external" in event.get("registration", {})
        
        # Build schema.org event
        transformed = {
            "@type": "Event",
            "name": name,
            "url": f"{EVENT_DETAIL_URL_PREFIX}{slug}",
        }
        
        # Add subtitle description if available
        if description:
            transformed["name"] = f"{name} - {description}"
        
        # Handle datetime
        if "startDate" in scheduling:
            transformed["startDate"] = parse_datetime(scheduling["startDate"])
        if "endDate" in scheduling:
            transformed["endDate"] = parse_datetime(scheduling["endDate"])
            
        # Add image
        main_image = event.get("mainImage", {})
        if "url" in main_image:
            transformed["image"] = main_image["url"]
            
        # Get long description for non-external events
        if not is_external:
            long_desc = fetch_event_detail(slug, session)
            if long_desc:
                transformed["description"] = long_desc
                
        # Add registration info
        registration = event.get("registration", {})
        if is_external and "external" in registration:
            transformed["sameAs"] = registration["external"]["registration"]
        elif "ticketing" in registration:
            ticketing = registration["ticketing"]
            transformed["offers"] = {
                "@type": "Offer",
                "availability": "InStock" if not ticketing.get("soldOut", False) else "SoldOut"
            }
            
        return transformed
        
    except Exception as e:
        logger.error(f"Error transforming event {event.get('slug', 'unknown')}: {e}")
        logger.error(f"Event URL: {EVENT_DETAIL_URL_PREFIX}{event.get('slug', 'unknown')}")
        return None


def fetch_events():
    """Fetch events from Sabha website"""
    session = get_cached_session()
    
    try:
        logger.info(f"Fetching events from: {EVENTS_URL}")
        response = session.get(EVENTS_URL)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        script_tag = soup.find("script", {"type": "application/json", "id": "wix-warmup-data"})
        
        if not script_tag:
            logger.error("No wix-warmup-data script found")
            return []
            
        data = json.loads(script_tag.string)
        logger.info(f"Found warmup data, main keys: {list(data.keys())}")
        
        # Navigate to events data
        apps_data = data.get("appsWarmupData", {}).get("140603ad-af8d-84a5-2c80-a0f60cb47351", {})
        logger.info(f"Apps data keys: {list(apps_data.keys())}")
        
        events = []
        for key, value in apps_data.items():
            if isinstance(value, dict) and "events" in value and "events" in value["events"]:
                event_list = value["events"]["events"]
                logger.info(f"Found {len(event_list)} events in key '{key}'")
                events.extend(event_list)
                
        logger.info(f"Total raw events found: {len(events)}")
        
        # Transform events
        transformed_events = []
        for event in events:
            transformed = transform_event(event, session)
            if transformed:
                transformed_events.append(transformed)
                
        logger.info(f"Total transformed events: {len(transformed_events)}")
        return transformed_events
        
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        return []


def main():
    events = fetch_events()
    
    with open("out/sabha.json", "w") as f:
        json.dump(events, f, indent=2)
        
    print(f"[SABHA] {len(events)} events")


if __name__ == "__main__":
    main()
