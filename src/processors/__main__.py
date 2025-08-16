#!/usr/bin/env python3

import sqlite3
import json
import re
import importlib
import pkgutil
import logging
from typing import List, Type
from .base import Processor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def discover_processors() -> List[Type[Processor]]:
    """Discover all processor classes in the processors package."""
    processors = []

    # Import all modules in the processors package
    import src.processors as processors_package

    for importer, modname, ispkg in pkgutil.iter_modules(
        processors_package.__path__, processors_package.__name__ + "."
    ):
        if modname.endswith(".__main__") or modname.endswith(".base"):
            continue
        try:
            module = importlib.import_module(modname)
            # Find all classes that inherit from Processor
            for name in dir(module):
                obj = getattr(module, name)
                if (
                    isinstance(obj, type)
                    and issubclass(obj, Processor)
                    and obj is not Processor
                ):
                    processors.append(obj)
        except Exception as e:
            logger.error(f"Error importing processor module {modname}: {e}")

    # Sort by priority (lower numbers first)
    processors.sort(key=lambda p: getattr(p, "PRIORITY", 100))
    return processors


def should_process_url(processor_class: Type[Processor], url: str) -> bool:
    """Check if processor should handle this URL based on URL_REGEX."""
    regex = getattr(processor_class, "URL_REGEX", None)
    if regex is None:
        return True  # Process all URLs if no regex specified
    return bool(re.match(regex, url))


def process_events():
    """Main function to process all events with all processors."""
    # Connect to database
    conn = sqlite3.connect("events.db")
    cursor = conn.cursor()

    # Discover processors
    processors = discover_processors()
    logger.info(
        f"Discovered {len(processors)} processors: {[p.__name__ for p in processors]}"
    )

    # Get all events
    cursor.execute("SELECT rowid, url, event_json FROM events")
    events = cursor.fetchall()
    logger.info(f"Processing {len(events)} events")

    modified_count = 0

    for rowid, url, event_json_str in events:
        try:
            event = json.loads(event_json_str)
            original_event = json.dumps(event, sort_keys=True)

            # Process with each applicable processor
            for processor_class in processors:
                if should_process_url(processor_class, url):
                    try:
                        result = processor_class.process(url, event)
                        if result is not None:
                            event = result
                    except Exception as e:
                        logger.error(
                            f"Error in processor {processor_class.__name__} for URL {url}: {e}"
                        )

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

    logger.info(f"Processing complete. Modified {modified_count} events")


if __name__ == "__main__":
    process_events()
