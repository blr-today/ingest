# HACKING

This project requires Python 3.14 and uses `uv` to manage its dependencies.

## Setup
```
uv sync --frozen --extra test
```

Run the complete ingestion pipeline with the same Makefile entry point used by
GitHub Actions:

```
uv run make clean && uv run make -s all
```

To import already-fetched event data into `events.db`, use `src.build`. An
optional `out/` JSON path limits the import to that file:

```
uv run python -m src.build
uv run python -m src.build out/bcc.json
```

Run Python modules from the repository root with `python -m src.<module>`.
Use `src.*` for absolute project imports; relative imports within a `src`
package are also valid. No `PYTHONPATH` setup is needed.

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
   from src.common.session import get_cached_session
   session = get_cached_session()
   response = session.get(url)
   ```

2. **`Fetch` class** - When you need browser impersonation (curl_cffi)
   ```python
   from src.common.fetch import Fetch
   fetcher = Fetch(browser="chrome")  # or "safari260_ios"
   response = fetcher.get(url=url)
   response = fetcher.post(url=url, json=payload)
   ```

   Use `Fetch` when:
   - API requires browser fingerprinting
   - Getting blocked by bot detection
   - Need to impersonate specific browser

### Code Standards
- **Python**: 3.14+, concise and idiomatic
- **Logging**: Support `LOG_LEVEL` env var, minimal logging in detail functions
- **Error handling**: Drop malformed events, log anomalies with URLs
- **Critical attributes**: Validate required fields (`title`, `slug`) - drop if missing

### Data Processing
- **Date filtering**: Only future events (today or later)
- **Schema.org compliance**: Use proper `@type: Event` structure
- **External links**: Use `sameAs` property, not `offers`
- **Rich text**: Convert to plain text for descriptions (use BeautifulSoup)
- **Timezone**: Use `from src.common.tz import IST` for Indian Standard Time

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

Run with: `uv run python -m src.jsonnet out/source.jsonnet`

## Processors

Post-processing logic in `src/processors/`, run after the build in the order of `PROCESSORS` in `registry.py`; add new classes there in order.
Any exception stops the run, so handle known bad data and log a warning with the URL.

```python
from .base import Processor

class MyProcessor(Processor):
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

## Event types and tags

- **Sources** set a specific `@type` when they know it.
- **Source processors** (AllEvents, District, HighApe, Koota, BhaagoIndia) fix one source's data, such as a type it stamps on everything.
- **`eventtype.py`** owns general typing from names, descriptions and keywords, and only fills a missing or plain `Event` type.
- **`src/tagger.py`** owns activity tags from `src/common/activities.py`: name rules, Jev answers, KIDS, MOVIE-SCREENING and WOMEN-ONLY, plus Jev typing for events still left as `Event`. It skips events with an `EXCLUDE` tag, and reads the same names as `eventtype.py` for tags instead of types, so their rules overlap on purpose.
- **`post-build.sql`** runs between the processors and the tagger and owns curation: exclusion and quality tags, area and source tags, ONLINE, BSF/MULTIDAY, CURATED, data fixes, deletions and keyword cleanup. It keeps specific type or tag overrides for named events, venues and organisers; general rules for types and activity tags go in `eventtype.py` and the tagger. Its `->>` needs SQLite 3.38.
