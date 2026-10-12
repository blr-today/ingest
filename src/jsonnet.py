import json
import _jsonnet
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


def transform(stem, raw_text):
    transformation_f = os.path.join("transform", stem + ".jsonnet")
    if not os.path.exists(transformation_f):
        raise Exception(f"Could not find {transformation_f}")
    output_json = _jsonnet.evaluate_file(
        transformation_f,
        tla_vars={"INPUT": raw_text},
        native_callbacks={
            "html2text": (("html",), html2text),
            # Use Python datetime
            "today": ((), today),
        },
    )
    return json.loads(output_json)
