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