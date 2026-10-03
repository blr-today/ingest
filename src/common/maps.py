import base64
import json
import re

from .session import get_cached_session

session = get_cached_session(
    cache_name="google-maps", days=90, allowable_codes=(200, 301, 302)
)
HEADERS = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"
}
PLACE = re.compile(
    r'\["0x[0-9a-f]+:0x[0-9a-f]+","((?:[^"\\]|\\.)*)",\[([\d.-]+),([\d.-]+)\]'
)


def place_id(url):
    match = re.search(r"[?&]cid=(\d+)", url)
    if match:
        return match.group(1)
    match = re.search(r"query_place_id=(ChIJ[\w-]+)", url)
    if match:
        raw = base64.urlsafe_b64decode(
            match.group(1) + "=" * (-len(match.group(1)) % 4)
        )
        return str(int.from_bytes(raw[12:20], "little"))
    if re.match(r"https?://(maps\.app\.goo\.gl|goo\.gl/maps)/", url):
        res = session.get(url, headers=HEADERS, allow_redirects=False)
        url = res.headers.get("location", "")
    match = re.search(r"0x[0-9a-f]+:0x([0-9a-f]+)", url)
    return str(int(match.group(1), 16)) if match else None


def resolve(url):
    # The embed page carries the address and coordinates without a login
    cid = place_id(url)
    if not cid:
        return None
    res = session.get(
        "https://maps.google.com/maps",
        params={"cid": cid, "output": "embed"},
        headers=HEADERS,
    )
    match = PLACE.search(res.text)
    if not match:
        return None
    address = json.loads(f'"{match.group(1)}"')
    return address, float(match.group(2)), float(match.group(3))
