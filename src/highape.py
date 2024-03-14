import requests
import json

def scrape_highape(location):
    base_url = "https://highape.com/api/search_algolia"
    total_results = 0
    
    # Iterate through pages until all results are scraped
    page = 0
    total = None
    while True:
        params = {
            "location": location,
            "event_request": 1,
            "algolia_page": page
        }
        response = requests.get(base_url, params=params)
        data = response.json()
        
        # Check if there are no more results
        total = data['event_results']['nbHits']
        

        if type(data['event_results']['hits']) == list:
        	for item in data['event_results']['hits']:
        		yield f"https://highape.com/{location}/events/{item['event_link']}"	
        else:
        	for item in data['event_results']['hits'].values():
        		yield f"https://highape.com/{location}/events/{item['event_link']}"

        if (page+1)*10 > total:	
        	break
        else:
        	page+=1

# Example usage:
location = "bangalore"
for url in scrape_highape(location):
	print(url)