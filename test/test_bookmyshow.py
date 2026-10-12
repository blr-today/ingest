import json

from common import bookmyshow
from src.processors.bookmyshow import BookMyShow, _seen

LINK = "https://in.bookmyshow.com/plays/tughlaq/ET00505270"
STATE = {
    "eventsSynopsisApi": {
        "queries": {
            "getPrimaryData": {
                "data": {
                    "widgets": {
                        "ABOUT_THE_EVENT": {
                            "cards": [{}, {"text": [{"text": "<p>A play about</p><p>a sultan.</p>"}]}]
                        }
                    }
                }
            }
        }
    }
}
EVENT = {"@type": "TheaterEvent", "description": "Book tickets online", "typicalAgeRange": "8+"}
HTML = (
    f'<script type="application/ld+json">[{json.dumps(EVENT)}]</script>'
    f"<script>window.__INITIAL_STATE__ = {json.dumps(STATE)};</script>"
)


def test_parse_prefers_synopsis():
    assert bookmyshow.parse(HTML) == {
        "typicalAgeRange": "8+",
        "description": "A play about\na sultan.",
    }


def test_processor_fills_only_gaps():
    _seen[LINK] = {"typicalAgeRange": "8+", "description": "About"}
    event = BookMyShow.process("u", {"sameAs": LINK, "typicalAgeRange": "16+"})
    assert event == {"sameAs": LINK, "typicalAgeRange": "16+", "description": "About"}


def test_other_links_are_ignored():
    event = {"sameAs": "https://in.bookmyshow.com/explore/plays"}
    assert BookMyShow.process("u", dict(event)) == event
