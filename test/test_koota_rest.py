from processors.koota import apply_record, plain_text

RECORD = {
    "content": {"rendered": '\n<p class="wp-block-paragraph">Local &amp; fresh.</p>\n\n<ul><li>One</li></ul>'},
    "class_list": ["post-1", "event_type-food"],
}


class TestKoota:
    def test_plain_text(self):
        text = plain_text(RECORD["content"]["rendered"])
        assert "<" not in text and "Local & fresh." in text

    def test_apply_record(self):
        event = {"@type": "Event", "description": "<!-- wp:paragraph -->x"}
        apply_record(event, RECORD)
        assert event["@type"] == "FoodEvent"
        assert event["description"].startswith("Local & fresh.")
