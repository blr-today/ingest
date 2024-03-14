import http.client
import datetime
from lxml import html
import json
import http.client
import datefinder

def make_request(url):
    parsed_url = url.split("://")[1]
    host, path = parsed_url.split("/")
    conn = http.client.HTTPSConnection(host)
    conn.request("GET", path, headers={
        "accept": "*/*",
        "user-agent": "gardencitybot/0.0.1"
    })
    response = conn.getresponse()
    return response.status, response.read().decode("utf-8")

def apply_xpath(html_content, xpath_selector):
    tree = html.fromstring(html_content)
    return tree.xpath(xpath_selector)

def fetch_events():
    url = "https://linktr.ee/atta_galatta"
    status_code, content = make_request(url)
    xpath_selector = '//a[@rel="noopener" and @target="_blank" and not(@data-testid="SocialIcon")]'
    filtered_links = apply_xpath(content, xpath_selector)

    events = []
    for link in filtered_links:
        title = link.xpath('.//p[1]//text()')[0]
        # TODO: Pick the date that is in the near future.
        tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        dates = list(datefinder.find_dates(title, index=True))
        if dates:
            date = dates[-1][0]
            idx = dates[-1][1][0]
            events.append({
                "title": title[0:idx],
                "starttime": dates[-1][0].replace(tzinfo=tz).isoformat(),
                'url': link.attrib['href']
            })

    return events

if __name__ == "__main__":
    # write to atta_galatta.json
    with open("out/atta_galatta.json", "w") as f:
        json.dump(fetch_events(), f, indent=2)