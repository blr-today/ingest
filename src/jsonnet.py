import json
import _jsonnet
import sys
import os

input_file = sys.argv[1]
if not os.path.exists(input_file):
    raise f"Input {input_file} not found"

basename = os.path.splitext(os.path.basename(input_file))[0]

with open(input_file, 'r') as json_file:
    input_json = json_file.read()

    transformation_f = os.path.join("transform", basename + ".jsonnet")
    if os.path.exists(transformation_f):
        output_json = _jsonnet.evaluate_file(transformation_f, tla_vars={'INPUT': input_json})
    else:
        raise f"Could not find {transformation_f}"

    output_json_file = os.path.join("out", basename + ".json")
    with open(output_json_file, "w") as output_file:
        output_file.write(output_json)
        print(f"JSON data saved to {output_json_file}")