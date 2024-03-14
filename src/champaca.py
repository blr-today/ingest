import http.client
import datetime
import json
import dateutil.parser
from lxml import etree
import datefinder

def make_request(url):
    parsed_url = url.split("://")[1]
    host, path = parsed_url.split("/", 1)
    conn = http.client.HTTPSConnection(host)
    conn.request("GET", "/" + path)
    response = conn.getresponse()
    return response.read()

def fetch_events():
    url = "https://champaca.in/blogs/events.atom"
    content = make_request(url)

    # Parse the XML content
    tree = etree.fromstring(content)

    events = []

    # Iterate over each entry in the feed
    for entry in tree.xpath('//xmlns:entry', namespaces={"xmlns": "http://www.w3.org/2005/Atom"})[0:5]:
        title = entry.find('.//xmlns:title', namespaces={"xmlns": "http://www.w3.org/2005/Atom"}).text

        # Find future dates in the title
        future_dates = list(datefinder.find_dates(title, index=True, source=True))
        if future_dates:
            # Get the first future date found
            future_date = next((date for date, idx, src in future_dates if date > datetime.datetime.now()), None)
            if future_date:
                # Calculate the difference in days between now and the future date
                days_difference = (future_date - datetime.datetime.now()).days
                if days_difference <= 30 and days_difference >= 1:
                    tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))  # Asia/Kolkata timezone
                    events.append({
                        "title": title,
                        "starttime": future_date.replace(tzinfo=tz).isoformat(),
                    })

    return events

if __name__ == "__main__":
    # write to champaca.json
    with open("out/champaca.json", "w") as f:
        json.dump(fetch_events(), f, indent=2)
