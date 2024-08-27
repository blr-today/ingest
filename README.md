# blr.today ingestion

This is the source code for the BLR.Today ingestion pipeline. This code does the following:

1. Fetches events from dozens of sources.
2. Enriches events with metadata, and cleanup. For example - location information is added where possible,
   and events are classified using schema.org/Event sub-types.
3. Events are exported in the `schema.org/Event` schema to a SQLite database.

## Status

The following sources are automatically ingested, filtered to just Bangalore events
wherever necessary.

- Ace of Pubs
- Adidas Runners
- AllEvents.in
- Atta Gallata
- Bangalore International Center
- Bengaluru Sustainability Forum
- Bhaago India
- Blue Tokai Events
- Carbon Science Gallery
- Champaca
- Courtyard Koota
- Creative Mornings BLR
- Gully Tours
- HighApe.com
- Townscript - Known Hosts only
- Musuem of Art & Photography
- Max Mueller Bhavan
- Paytm Insider
- PVR Cinema Movie Screenings
- Skillboxes
- Sofar
- Sumukha Gallery
- The Courtyard
- Together.buzz
- Tonight.is
- Total Environment Music Events (Windmills)
- Trove Experiences
- Venn
- Zomato Events

A lot more are in-progress, please see [`TODO.md`](TODO.md) for a more updated list.

## Dependencies:

- curl_impersonate
- python3
- jq
- Python packages listed in `pyproject.toml`

## Running

The code automatically runs using GitHub Actions once every four hours. You can run it using the following command:

`make clean && make`. Once complete, the `events.db` file will be updated with the latest events.

## License

This repository is licensed under the GNU-GPLv3 license. This means that you can use, modify, and distribute this code as long as you also release your code under the same license. Please see `LICENSE.txt` for more details.

The files stored in `out/` and `fixtures/` directories is copyright of the original authors and is not covered by this license. Instead of using this, please use the published dataset available at
blr.today/dataset, which is published under the [Open Database License](https://opendatacommons.org/licenses/odbl/1.0/), which means you must attribute the data, and share it under the same license without any technical
restrictions.
