import json
from types import SimpleNamespace

from common.shopify import Shopify, ShopifyVariant, html2txt

FIXTURE = "test/fixtures/shopify/products.json"


class FakeResponse:
    def __init__(self, data):
        self.data = data
        self.encoding = None
        self.raised = False

    def raise_for_status(self):
        self.raised = True

    def json(self):
        return self.data


def shop(collection=None):
    seen = []
    response = FakeResponse(json.load(open(FIXTURE)))

    def get(url):
        seen.append(url)
        return response
    return Shopify("thewhiteboxco.in", SimpleNamespace(get=get), collection), seen, response


def test_collection_url():
    s, _, _ = shop("events-of-the-month")
    assert s.url == "https://thewhiteboxco.in/collections/events-of-the-month/products.json"
    assert Shopify("x.in", None).url == "https://x.in/products.json"


def test_products_are_parsed():
    s, seen, response = shop("events-of-the-month")
    first, second = list(s.products())
    assert seen == [s.url]
    assert response.encoding == "utf-8" and response.raised
    assert first.title == "Cupid's Soirée - Singles Mixer"
    assert first.url == "https://thewhiteboxco.in/products/cupids-soiree-singles-mixer-new"
    assert first.variants[0] == ShopifyVariant(
        price="3000.00", sku=None, title="Early Bird - Lady's Pass / BLR | Sept 27 | 12 PM | Brine"
    )
    assert len(first.variants) == 4
    assert "Sept 27" in first.description and "<p>" not in first.description
    assert second.handle == "mixology-workshop-bangalore-1"


def test_html2txt_drops_links_and_markup():
    text = html2txt('<p>Hello <a href="https://x.com">there</a></p>')
    assert text.strip() == "Hello there"
