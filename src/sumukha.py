from bs4 import BeautifulSoup
from common.session import get_cached_session
import html
import json
from urllib.parse import urlparse, urljoin
from datetime import datetime, timedelta

session = get_cached_session()


# Function to parse and format date
def parse_and_format_date(date_str):
    try:
        d1 = datetime.strptime(date_str, "%d %B").replace(year=datetime.now().year)
        d2 = d1.replace(year=datetime.now().year + 1)
        if abs(d1 - datetime.now()) < abs(d2 - datetime.now()):
            return d1.strftime("%Y-%m-%d")
        else:
            return d2.strftime("%Y-%m-%d")
    except:
        return datetime.strptime(date_str, "%d %B %Y").strftime("%Y-%m-%d")


def fetch_description(url):
    # Fetch event description from detail page
    event_html = session.get(url).text
    # Get the description by getting all text between "converter.makeHtml(`" and "`"
    start_index = event_html.find("converter.makeHtml(`") + len("converter.makeHtml(`")
    end_index = event_html.find("`);", start_index)
    description = event_html[start_index:end_index]
    # decode html entities
    return html.unescape(description)


# Function to parse event details from HTML
def parse_event_details(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    events = []
    for card_body in soup.select(".card-body"):
        parent_div = card_body.parent.parent
        title = card_body.select_one(".list-title a").text.strip().title()
        performer = card_body.select_one(".text-muted").text.strip()
        date_range = card_body.select_one("div.text-muted").text.strip()
        start_date_str, end_date_str = [date.strip() for date in date_range.split("to")]
        start_date = parse_and_format_date(start_date_str)
        end_date = parse_and_format_date(end_date_str)
        img_src = parent_div.select_one("img")["src"]

        event_url = urljoin(
            "https://sumukha.com", card_body.select_one(".list-title a")["href"]
        )
        description = fetch_description(event_url)

        events.append(
            {
                "name": title,
                "startDate": start_date,
                "endDate": end_date,
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                "url": event_url,
                "image": urljoin("https://sumukha.com", img_src),
                "description": description,
                "performer": {
                    "@type": "PerformingGroup",
                    "name": performer.replace("by ", ""),
                },
            }
        )
    return events


def main():
    events = []
    for scope in ["current", "upcoming"]:
        url = f"https://sumukha.com/exhibition?section=exhibition&scope={scope}"
        html_content = session.get(url).text
        events += parse_event_details(html_content)

    with open("out/sumukha.json", "w") as f:
        json.dump(events, f, indent=2)

    print(f"[SUMUKHA] {len(events)} events")


if __name__ == "__main__":
    main()
