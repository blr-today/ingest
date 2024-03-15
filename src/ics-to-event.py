import sys
import ics
import json


def convert_ics_to_json(ics_file_path):
    """
    Convert ICS calendar file to JSON-LD containing schema.org events.

    Args:
        ics_file_path (str): Path to the ICS file.

    Returns:
        str: JSON-LD string containing schema.org events.
    """
    events = []

    with open(ics_file_path, 'r') as file:
        calendar = ics.Calendar(file.read())

    for event in calendar.events:
        event_json = {
            "@context": "http://schema.org",
            "@type": "Event",
            "name": event.name,
            "startDate": event.begin.isoformat(),
            "endDate": event.end.isoformat(),
            "description": event.description,
            "location": {
                "@type": "Place",
                "name": event.location
            },
            "url": event.url,
            "keywords": ", ".join(sorted(event.categories)),
        }

        # Check for attachments (if image)
        if event.extra:
            for line in event.extra:
                if line.name == "ATTACH" and line.value.startswith("https"):
                    event_json["image"] = line.value
                    break

        events.append(event_json)

    return json.dumps(events, indent=2)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py input_ics_file output_json_file")
        sys.exit(1)

    input_ics_file = sys.argv[1]
    output_json_file = sys.argv[2]

    json_data = convert_ics_to_json(input_ics_file)
    
    with open(output_json_file, 'w') as output_file:
        output_file.write(json_data)
    
    print(f"JSON data saved to {output_json_file}")
