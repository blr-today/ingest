from types import SimpleNamespace

from common import maps

EMBED = "test/fixtures/maps/embed.html"
PLACE = (
    "https://www.google.com/maps/place/Mountain+Bee+Kombucha+Hive/@12.9813299,77.6336833,904m/"
    "data=!3m2!1e3!4b1!4m6!3m5!1s0x3bae171b42bff939:0xc25a4250d42663c1!8m2!3d12.9813299!4d77.6362582"
)


def fake_get(monkeypatch, **response):
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        return SimpleNamespace(**response)
    monkeypatch.setattr(maps, "session", SimpleNamespace(get=get))
    return calls


def test_place_id_reads_cid_param():
    assert maps.place_id("https://maps.google.com/?cid=14004578906186081217&hl=en") == "14004578906186081217"


def test_place_id_decodes_query_place_id():
    url = "https://www.google.com/maps/search/?api=1&query=Google&query_place_id=ChIJibah5rEXrjsRBqh68oiwMcM"
    assert maps.place_id(url) == "14065217213484935174"


def test_place_id_reads_feature_id_hex():
    assert maps.place_id(PLACE) == "14004578906186081217"


def test_place_id_follows_short_links(monkeypatch):
    calls = fake_get(monkeypatch, headers={"location": PLACE})
    assert maps.place_id("https://maps.app.goo.gl/Gtmq3fERxindsCn37") == "14004578906186081217"
    assert calls[0][0] == "https://maps.app.goo.gl/Gtmq3fERxindsCn37"
    assert calls[0][1]["allow_redirects"] is False


def test_place_id_unknown_url():
    assert maps.place_id("https://example.com/venue") is None


def test_short_link_without_redirect(monkeypatch):
    fake_get(monkeypatch, headers={})
    assert maps.place_id("https://goo.gl/maps/abc") is None


def test_resolve_reads_embed_page(monkeypatch):
    calls = fake_get(monkeypatch, text=open(EMBED).read())
    address, lat, lng = maps.resolve(PLACE)
    assert address.startswith("Mountain Bee Kombucha Hive, 479, 2nd Main Rd")
    assert address.endswith("Bengaluru, Karnataka 560038, India")
    assert (lat, lng) == (12.9813299, 77.6362582)
    assert calls[0][1]["params"] == {"cid": "14004578906186081217", "output": "embed"}


def test_resolve_without_place():
    assert maps.resolve("https://example.com/venue") is None


def test_resolve_without_match(monkeypatch):
    fake_get(monkeypatch, text="<html></html>")
    assert maps.resolve(PLACE) is None
