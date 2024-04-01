import http.client
from bs4 import BeautifulSoup
import html
import json
from urllib.parse import urlparse, urljoin
from datetime import datetime

# Function to fetch HTML content using http.client
def fetch_html(url):
    parsed_url = urlparse(url)
    conn = http.client.HTTPSConnection(parsed_url.netloc)
    conn.request("GET", parsed_url.path + "?" + parsed_url.query)
    response = conn.getresponse()
    return response.read().decode()

# Function to parse and format date
def parse_and_format_date(date_str):
    try:
        d1 = datetime.strptime(date_str, "%d %B").replace(year=datetime.now().year)
        d2 = d1.replace(year=datetime.now().year+1)
        if abs(d1 - datetime.now()) < abs(d2 - datetime.now()):
            return d1.strftime("%Y-%m-%d")
        else:
            return d2.strftime("%Y-%m-%d")
    except:
        return datetime.strptime(date_str, "%d %B %Y").strftime("%Y-%m-%d")

def fetch_description(url):
    # Fetch event description from detail page
    event_html = fetch_html(url)
    # Get the description by getting all text between "converter.makeHtml(`" and "`"
    start_index = event_html.find("converter.makeHtml(`") + len("converter.makeHtml(`")
    end_index = event_html.find("`);", start_index)
    description = event_html[start_index:end_index]
    # decode html entities
    return html.unescape(description)

# Function to parse event details from HTML
def parse_event_details(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    events = []
    for card_body in soup.select('.card-body'):
        parent_div = card_body.parent.parent
        title = card_body.select_one('.list-title a').text.strip().title()
        performer = card_body.select_one('.text-muted').text.strip()
        date_range = card_body.select_one('div.text-muted').text.strip()
        start_date_str, end_date_str = [date.strip() for date in date_range.split('to')]
        start_date = parse_and_format_date(start_date_str)
        end_date = parse_and_format_date(end_date_str)
        img_src = parent_div.select_one('img')['src']

        event_url = urljoin('https://sumukha.com', card_body.select_one('.list-title a')['href'])
        description = fetch_description(event_url)

        events.append({
            "@context": "https://schema.org",
            "@type": "ExhibitionEvent",
            "name": title,
            "startDate": start_date,
            "endDate": end_date,
            "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "eventStatus": "https://schema.org/EventScheduled",
            "location": {
                "@type": "Place",
                "name": "Gallery Sumukha",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "24/10, BTS Depot Road, Wilson Garden",
                    "addressLocality": "Bengaluru",
                    "postalCode": "560027",
                    "addressCountry": "IN"
                },
                "telephone": "+91 93804 20041",
                "email": "info@sumukha.com"
            },
            "image": urljoin('https://sumukha.com', img_src),
            "description": description,
            "performer": {
                "@type": "PerformingGroup",
                "name": performer.replace("by ","")
            },
            "organizer": {
                "@type": "Organization",
                "name": "Gallery Sumukha",
                "url": "https://sumukha.com/"
            }
        })
    return events

# Main function to orchestrate the fetching, parsing, and saving process
def main():
    url = 'https://sumukha.com/exhibition'
    html_content = fetch_html(url)
    events = parse_event_details(html_content)

    # Save the data to a JSON file
    with open('out/sumukha.json', 'w') as f:
        json.dump(events, f, indent=2)

    print("JSON file with exhibition events created successfully.")

# Adapt this script for real-world execution as needed.

if __name__ == '__main__':
    main()