import sys
import datetime
import json
import pytz
from common import icalendar

tz = pytz.timezone('Asia/Kolkata')

def fix_date(date_str):
    d = datetime.datetime.fromisoformat(date_str)
    d.replace(tzinfo=tz)
    return d.isoformat()

def modify_event(event):
    event['keywords'] = [x.strip() for x in event['keywords'][0].split(",")]
    event['name'] = event['name'].split("|")[0].strip()
    if event['description'] == "":
        event['description'] = "A Pub hosted by Ace of Pubs"
    event['startDate'] = fix_date(event['startDate'])
    event['endDate'] = fix_date(event['endDate'])
    event['keywords'] = "QUIZ"
    return event

if __name__ == "__main__":
    input_ics_file = "out/aceofpubs.ics"
    output_json_file = "out/aceofpubs.json"

    json_data = icalendar.convert_ics_to_events(input_ics_file)
    json_data = [modify_event(event) for event in json_data]
    
    with open(output_json_file, 'w') as output_file:
        output_file.write(json.dumps(json_data, indent=2))
    
    print(f"JSON data saved to {output_json_file}")
