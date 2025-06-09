import sys
import json
from common import icalendar

# TODO: Move the BIC code to bic.py
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python ics-to-event.py input_ics_file output_json_file")
        sys.exit(1)

    input_ics_file = sys.argv[1]
    output_json_file = sys.argv[2]

    try:
        with open(input_ics_file, "r") as file:
            if len(file.read()) == 0:
                skip = True
    except FileNotFoundError:
        skip = True

    if skip:
        print("[BSF] ICS Calendar is invalid or empty")
    else:
        json_data = icalendar.convert_ics_to_events(input_ics_file)

        with open(output_json_file, "w") as output_file:
            output_file.write(json.dumps(json_data, indent=2))

        print(f"JSON data saved to {output_json_file}")
