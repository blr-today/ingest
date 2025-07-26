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
- **Name**: `src/venue_name.py` (lowercase, underscores)
- **Output**: `out/venue_name.json` with event count log `[VENUE] N events`
- **Dependencies**: Use existing packages from `pyproject.toml`

### Code Standards
- **Python**: 3.13+ compliant, concise and idiomatic
- **Logging**: Support `LOG_LEVEL` env var, minimal logging in detail functions
- **Error handling**: Drop malformed events, log anomalies with URLs
- **Critical attributes**: Validate required fields (`title`, `slug`) - drop if missing

### Data Processing
- **Date filtering**: Only future events (today or later)
- **Schema.org compliance**: Use proper `@type: Event` structure
- **External links**: Use `sameAs` property, not `offers`
- **Rich text**: Convert to plain text for descriptions
- **Session**: Use `get_cached_session()` for HTTP requests

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
  "sameAs": "https://external-registration.com"  # for external events
}
```

### Patch Files
Create `patch/source.json` with common metadata:

- Location details (address, coordinates, phone)
- Organizer information
- Keywords for categorization
- ISIC classification codes
