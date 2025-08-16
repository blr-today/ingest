import json
import _jsonnet
import sys
import os
import html2text as HT
import datetime


def html2text(html):
    h = HT.HTML2Text()
    h.ignore_links = True
    h.bypass_tables = True
    h.single_line_break = True
    return h.handle(html).strip()


def today():
    return datetime.datetime.today().strftime("%Y-%m-%d")


input_file = sys.argv[1]
if not os.path.exists(input_file):
    print(f"Input {input_file} not found")
    sys.exit(1)

basename = os.path.splitext(os.path.basename(input_file))[0]

with open(input_file, "r") as json_file:
    input_json = json_file.read()

    transformation_f = os.path.join("transform", basename + ".jsonnet")
    if os.path.exists(transformation_f):
        output_json = _jsonnet.evaluate_file(
            transformation_f,
            tla_vars={"INPUT": input_json},
            native_callbacks={
                "html2text": (("html",), html2text),
                # Use Python datetime
                "today": ((), today),
            },
        )
    else:
        raise Exception(f"Could not find {transformation_f}")

    output_json_file = os.path.join("out", basename + ".json")
    with open(output_json_file, "w", encoding="utf-8") as output_file:
        output_file.write(output_json)
        eventCount = len(json.loads(output_json))
        print(f"[{basename.upper()}] {eventCount} events (jsonnet.py)")
