# HACKING

This project uses `uv` for its python tooling. While it is possible to
develop on this codebase without `uv` (nothing is `uv` specific),
it just makes things much easier.

## Setup
```
uv init
uv venv
uv pip install  -r pyproject.toml
make all
# or
python src/script.py
```

Once all the data is fetched, you can run the ingestion script
using:

`python src/event-fetch.py` with a file in the out directory
as an optional argument. So to just ingest the Bangalore Chess Club
events for example:

```
python src/event-fetch.py out/bcc.json
or
uv run src/event-fetch.py out/bcc.json
```

## Event Source Scraping Style Guide

### Script Structure
- **Name**: `src/sources/venue_name.py` (lowercase, underscores)
- **Output**: `out/venue_name.json` with event count log `[VENUE] N events`
- **Dependencies**: Use existing packages from `pyproject.toml`
- **Makefile**: Add target and include in `fetch` dependencies

### HTTP Requests

Two options depending on needs:

1. **`get_cached_session()`** - Standard requests with caching
   ```python
   from common.session import get_cached_session
   session = get_cached_session()
   response = session.get(url)
   ```

2. **`Fetch` class** - When you need browser impersonation (curl_cffi)
   ```python
   from ..common.fetch import Fetch
   fetcher = Fetch(browser="chrome")  # or "safari260_ios"
   response = fetcher.get(url=url)
   response = fetcher.post(url=url, json=payload)
   ```

   Use `Fetch` when:
   - API requires browser fingerprinting
   - Getting blocked by bot detection
   - Need to impersonate specific browser

### Code Standards
- **Python**: 3.13+ compliant, concise and idiomatic
- **Logging**: Support `LOG_LEVEL` env var, minimal logging in detail functions
- **Error handling**: Drop malformed events, log anomalies with URLs
- **Critical attributes**: Validate required fields (`title`, `slug`) - drop if missing

### Data Processing
- **Date filtering**: Only future events (today or later)
- **Schema.org compliance**: Use proper `@type: Event` structure
- **External links**: Use `sameAs` property, not `offers`
- **Rich text**: Convert to plain text for descriptions (use BeautifulSoup)
- **Timezone**: Use `from common.tz import IST` for Indian Standard Time

### Output Format
```python
{
  "@type": "Event",
  "name": "Event Title - Subtitle",
  "url": "https://venue.com/event-details/slug",
  "startDate": "2025-07-26T08:00:00+05:30",
  "endDate": "2025-07-26T09:20:00+05:30",
  "image": "https://...",
  "description": "Long description text",
  "location": {
    "@type": "Place",
    "name": "Venue Name",
    "address": "Full address",
    "geo": {
      "@type": "GeoCoordinates",
      "latitude": "12.9577",
      "longitude": "77.6328"
    }
  },
  "sameAs": "https://external-registration.com"  # for external events
}
```

### Patch Files
Create `patch/domain.json` (e.g., `patch/penciljam.json`) with common metadata:

```json
{
  "@context": "https://schema.org",
  "@type": "Event",
  "organizer": {
    "@type": "Organization",
    "name": "Organizer Name"
  },
  "keywords": ["KEYWORD"]
}
```

Patches are applied automatically based on the event URL's domain.

## Jsonnet Transformers

For APIs that return raw JSON needing transformation, create `transform/source.jsonnet`:

```jsonnet
local transformEvent(event) = {
  '@type': 'Event',
  name: event.title,
  startDate: event.date + "T" + event.time + "+05:30",
  // ... other fields
};

function(INPUT) [
  transformEvent(event)
  for event in std.parseJson(INPUT)
  if event.date >= std.native('today')()
]
```

Run with: `python src/jsonnet.py out/source.jsonnet`

## Processors

Post-processing logic in `src/processors/`. Processors run after events are in the database.

```python
from .base import Processor

class MyProcessor(Processor):
    PRIORITY = 90  # Lower runs first
    URL_REGEX = r"https://example\.com/.*"  # Optional: filter by URL

    @staticmethod
    def process(url, event):
        # Modify event dict
        event["keywords"] = event.get("keywords", []) + ["TAG"]
        return event
```

Key processors:
- `patch.py` - Applies patch files based on domain
- `geo.py` - Tags events >50km from Bangalore as NOTINBLR
- `schemafixer.py` - Fixes common schema issues

## Post-build SQL

`post-build.sql` runs after all processing for bulk updates:
- Tag low-quality events
- Mark events outside Bangalore
- Add location-based keywords (HSR, INDIRANAGAR, etc.)
- Delete duplicate/unwanted events

Uses SQLite JSON functions and REGEXP for pattern matching.
