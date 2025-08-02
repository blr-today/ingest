import html2text as HT
import json
from dataclasses import dataclass


def html2txt(html):
    h = HT.HTML2Text()
    h.ignore_links = True
    h.bypass_tables = True
    h.single_line_break = True
    return h.handle(html)


@dataclass
class ShopifyVariant:
    price: str
    sku: str
    title: str


@dataclass
class ShopifyProduct:
    title: str
    handle: str
    variants: list[ShopifyVariant]
    description: str
    url: str


class Shopify:
    def __init__(self, domain, session, collection=None):
        self.base_url = f"https://{domain}"
        if collection:
            self.url = f"{self.base_url}/collections/{collection}/products.json"
        else:
            self.url = f"{self.base_url}/products.json"
        self.session = session

    def products(self):
        r = self.session.get(self.url)
        # We force encoding as utf-8
        r.encoding = "utf-8"
        r.raise_for_status()
        for p in r.json()["products"]:
            yield ShopifyProduct(
                url=f"{self.base_url}/products/{p['handle']}",
                title=p["title"],
                handle=p["handle"],
                description=html2txt(p["body_html"]),
                variants=[
                    ShopifyVariant(price=v["price"], sku=v["sku"], title=v["title"])
                    for v in p["variants"]
                ],
            )
