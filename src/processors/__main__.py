#!/usr/bin/env python3

import json
import logging
import re
import sqlite3
from contextlib import closing

from .base import DROP
from .registry import PROCESSORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def should_process_url(processor_class, url):
    """Check if processor should handle this URL based on URL_REGEX."""
    regex = processor_class.URL_REGEX
    return regex is None or bool(re.match(regex, url))


def run_processors(url, event):
    """Run the matching processors in order, returning the event or DROP."""
    for processor_class in PROCESSORS:
        if should_process_url(processor_class, url):
            result = processor_class.process(url, event)
            if result == DROP:
                return DROP
            if result is not None:
                event = result
    return event


def process_events():
    """Process every event in events.db, stopping at the first unexpected error."""
    with closing(sqlite3.connect("events.db")) as conn:
        logger.info(
            f"Running {len(PROCESSORS)} processors: {[p.__name__ for p in PROCESSORS]}"
        )
        events = conn.execute("SELECT rowid, url, event_json FROM events").fetchall()
        logger.info(f"Processing {len(events)} events")

        modified_count = 0
        dropped_count = 0

        for rowid, url, event_json_str in events:
            try:
                event = json.loads(event_json_str)
                original_event = json.dumps(event, sort_keys=True)
                event = run_processors(url, event)
            except Exception as e:
                e.add_note(f"Processing failed for {url}")
                raise

            if event == DROP:
                conn.execute("DELETE FROM events WHERE rowid = ?", (rowid,))
                dropped_count += 1
            elif json.dumps(event, sort_keys=True) != original_event:
                conn.execute(
                    "UPDATE events SET event_json = ? WHERE rowid = ?",
                    (json.dumps(event), rowid),
                )
                modified_count += 1
                if modified_count % 20 == 0:
                    conn.commit()
                    logger.info(f"Committed {modified_count} modifications")

        conn.commit()

    logger.info(
        f"Processing complete. Modified {modified_count} events, dropped {dropped_count}"
    )


if __name__ == "__main__":
    process_events()
