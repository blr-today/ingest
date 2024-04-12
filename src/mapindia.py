import http.client
import json
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

# TODO: We do not track Exhibits yet, only events
# Function to format datetime for allDay events
def format_datetime(dt, all_day):
    tz = timezone(timedelta(hours=5, minutes=30))
    if all_day:
        return dt.strftime("%Y-%m-%d")
    else:
        return dt.replace(tzinfo=tz).isoformat()

start_ts = datetime.now().strftime("%Y-%m-%d")
end_ts = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

# Setup HTTP connection
conn = http.client.HTTPSConnection("map-india.org")

# Prepare parameters for the GET request
params = urlencode({
    'action': 'WP_FullCalendar',
    'type': 'event',
    'start': start_ts,
    'end': end_ts
})

# Perform the GET request
conn.request("GET", "/wp-admin/admin-ajax.php?" + params)
response = conn.getresponse()

# Check if the request was successful
if response.status == 200:
    data = json.loads(response.read())
    events = []

    for item in data:
        start_date = datetime.fromisoformat(item['start'])
        end_date = datetime.fromisoformat(item['end'])
        delta_days = (end_date - start_date).days + 1

        for day in range(delta_days):
            event_date = start_date + timedelta(days=day)
            closing_time = end_date.replace(year=event_date.year, month=event_date.month, day=event_date.day)
            event = {
                "name": item['title'],
                "startDate": format_datetime(event_date, item['allDay']),
                "endDate": format_datetime(closing_time, item['allDay']),
                "url": item['url']
            }
            # if not item['allDay']:
            #     event["startDate"] = event["startDate"].replace("00:00:00", item['start'].split("T")[1])
            #     event["endDate"] = event["endDate"].replace("00:00:00", item['end'].split("T")[1])
            events.append(event)

    # Write the events to a JSON file
    with open("out/mapindia.json", "w") as file:
        json.dump(events, file, indent=2)
else:
    print(f"Failed to fetch data. Status code: {response.status}")
