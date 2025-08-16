import requests
from bs4 import BeautifulSoup

def extract_event_urls(url="https://bhaagoindia.com/events/?city=bengaluru-4"):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all links that start with "/events/"
    event_links = soup.find_all('a', href=lambda x: x and x.startswith('/events/'))
    
    # Extract hrefs and filter out category, city, and base event URLs
    valid_urls = []
    for link in event_links:
        href = link.get('href')
        if href and is_valid_event_url(href):
            valid_urls.append(href)
    
    valid_urls = sorted(set(valid_urls))
    
    for url in valid_urls:
        print(f"https://bhaagoindia.com{url}")

def is_valid_event_url(href):
    """Check if the URL is a valid event URL based on path element count"""
    if not href or not href.startswith('/events/'):
        return False
    
    # Split path into elements and filter out empty ones
    path_elements = [elem for elem in href.split('/') if elem]
    
    # Valid event URLs should have exactly 2 path elements: ['events', 'event-name']
    # Invalid patterns:
    # - '/events/' or '/events' -> 1 element: ['events']
    # - '/events/category/something/' -> 3 elements: ['events', 'category', 'something']  
    # - '/events/city/something/' -> 3 elements: ['events', 'city', 'something']
    return len(path_elements) == 2

if __name__ == "__main__":
    extract_event_urls()
