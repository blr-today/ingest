# Writing a source

Each event source is one module under `src/sources/`. See [HACKING.md](HACKING.md)
for setup and for what happens to events after they are fetched.

## Script Structure
- **Name**: `src/sources/venue.py`; `venue` is the output stem and source keyword
- **Contract**: `events()` returns Event dicts and writes nothing; `python -m src.sources venue` writes `out/venue.json` and logs `[VENUE] N events`
- **Id**: optional `identifier` string, the event's blr.today id as is (`gcw.2026-11-01`); otherwise it comes from the url, see [HACKING.md](HACKING.md)
- **Dependencies**: Use existing packages from `pyproject.toml`
- **Makefile**: List `out/venue.json` in `fetch`; a raw download gets a rule plus `out/venue.json: out/venue.ics`

## HTTP Requests

1. **`get_cached_session()`** - Standard requests with caching
   ```python
   from src.common.session import get_cached_session
   session = get_cached_session()
   response = session.get(url)
   ```

2. **`Fetch` class** - Browser impersonation (curl_cffi) for sites with bot
   detection or fingerprinting
   ```python
   from src.common.fetch import Fetch
   fetcher = Fetch(browser="chrome")  # or "safari260_ios"
   response = fetcher.get(url=url)
   response = fetcher.post(url=url, json=payload)
   ```

## Code Standards
- **Python**: 3.14+, concise and idiomatic
- **Logging**: Support `LOG_LEVEL` env var, minimal logging in detail functions
- **Error handling**: Drop malformed events, log anomalies with URLs
- **Critical attributes**: Validate required fields (`title`, `slug`) - drop if missing

## Data Processing
- **Date filtering**: Only future events (today or later)
- **Schema.org compliance**: Use proper `@type: Event` structure
- **External links**: Use `sameAs` property, not `offers`
- **Rich text**: Convert to plain text for descriptions (use BeautifulSoup)
- **Timezone**: Use `from src.common.tz import IST` for Indian Standard Time

## Output Format
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

## Patch Files
Create `patch/domain.json` (e.g., `patch/penciljam.json`) with common metadata.
The Patch processor applies it to every event whose URL is on that domain:

```json
{"@type": "Event", "organizer": {"@type": "Organization", "name": "Organizer Name"}, "keywords": ["KEYWORD"]}
```

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

Return `transform("source", raw_text)` from `src/sources/source.py`'s `events()`.
