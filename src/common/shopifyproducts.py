from common.session import get_cached_session
import json

class ShopifyProducts:
    def __init__(self, url, collection = ""):
        self.url = f"{url}{collection}/products.json"
        self.session = get_cached_session()

    def fetch_products(self):
        res = self.session.get(self.url).text

        res_json = json.loads(res)
        return res_json['products']