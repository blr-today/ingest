from sources.thewhitebox import filter_products
from common.shopify import ShopifyProduct, ShopifyVariant


def product(handle, *variants):
    return ShopifyProduct(
        title=handle.replace("-", " "),
        handle=handle,
        url=f"https://thewhiteboxco.in/products/{handle}",
        description="",
        variants=[ShopifyVariant(title=v, price="100", sku="") for v in variants],
    )


def kept(*products):
    return list(filter_products(products))


class TestCityFilter:
    def test_single_non_blr_variant_dropped(self):
        p = product("cupids-soiree-mumbai", "Sat | Oct 12 | 4 PM | Mumbai")
        assert kept(p) == []

    def test_single_blr_variant_kept(self):
        p = product("mixer", "Lady's Pass / BLR | Oct 12 | 4 PM | Brine")
        assert kept(p) == [p]

    def test_no_city_kept(self):
        p = product("pottery", "Sat | Oct 12 | 4 PM | Studio")
        assert kept(p) == [p]

    def test_multi_variant_with_blr_kept(self):
        p = product("mixer", "Delhi | Oct 12 | 4 PM", "Bangalore | Oct 13 | 4 PM")
        assert kept(p) == [p]

    def test_multi_variant_no_blr_dropped(self):
        p = product("mixer", "Delhi | Oct 12 | 4 PM", "Pune | Oct 13 | 4 PM")
        assert kept(p) == []
