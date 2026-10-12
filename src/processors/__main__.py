#!/usr/bin/env python3

import json
import logging
import re
import sqlite3

from .base import DROP
from .registry import PROCESSORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def should_process_url(processor_class, url):
    """Check if processor should handle this URL based on URL_REGEX."""
    regex = processor_class.URL_REGEX
    return regex is None or bool(re.match(regex, url))


def process_events():
    """Main function to process all events with all processors."""
    # Connect to database
    conn = sqlite3.connect("events.db")
    cursor = conn.cursor()

    logger.info(
        f"Running {len(PROCESSORS)} processors: {[p.__name__ for p in PROCESSORS]}"
    )

    # Get all events
    cursor.execute("SELECT rowid, url, event_json FROM events")
    events = cursor.fetchall()
    logger.info(f"Processing {len(events)} events")

    modified_count = 0
    dropped_count = 0

    for rowid, url, event_json_str in events:
        try:
            event = json.loads(event_json_str)
            original_event = json.dumps(event, sort_keys=True)

            # Process with each applicable processor
            result = None
            for processor_class in PROCESSORS:
                if should_process_url(processor_class, url):
                    try:
                        result = processor_class.process(url, event)
                        if result == DROP:
                            break
                        if result is not None:
                            event = result
                    except Exception as e:
                        logger.error(
                            f"Error in processor {processor_class.__name__} for URL {url}: {e}"
                        )

            if result == DROP:
                cursor.execute("DELETE FROM events WHERE rowid = ?", (rowid,))
                dropped_count += 1
                continue

            # Check if event was modified
            if json.dumps(event, sort_keys=True) != original_event:
                # Update database
                cursor.execute(
                    "UPDATE events SET event_json = ? WHERE rowid = ?",
                    (json.dumps(event), rowid),
                )
                modified_count += 1

                # Commit every 20 modifications
                if modified_count % 20 == 0:
                    conn.commit()
                    logger.info(f"Committed {modified_count} modifications")

        except Exception as e:
            logger.error(f"Error processing event at URL {url}: {e}")

    # Final commit
    conn.commit()
    conn.close()

    logger.info(
        f"Processing complete. Modified {modified_count} events, dropped {dropped_count}"
    )


if __name__ == "__main__":
    process_events()
