import lxml.html
import json
import re
import lxml.etree

class JsonLdExtractor:
    _xp_jsonld = lxml.etree.XPath(
        'descendant-or-self::script[@type="application/ld+json"]'
    )

    def parse_html(self, html, encoding):
        """Parse HTML using lxml.html.HTMLParser, return a tree"""
        parser = lxml.html.HTMLParser(encoding=encoding)
        return lxml.html.fromstring(html, parser=parser)

    def extract(self, htmlstring, base_url=None, encoding="UTF-8"):
        tree = self.parse_html(htmlstring, encoding=encoding)
        return self.extract_items(tree, base_url=base_url)

    def extract_items(self, document, base_url=None):
        return [
            item
            for items in map(self._extract_items, self._xp_jsonld(document))  # type: ignore[arg-type]
            if items
            for item in items
            if item
        ]

    def _extract_items(self, node):
        script = node.xpath("string()")
        data = json.loads(script, strict=False)
        if isinstance(data, list):
            yield from data
        elif isinstance(data, dict):
            yield data