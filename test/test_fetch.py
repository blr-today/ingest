from common.fetch import Fetch
from requests_cache import CachedResponse
from requests_cache.models.response import OriginalResponse
from requests.models import PreparedRequest, Response as RequestsResponse
import pytest
import unittest

class TestFetch:

    @pytest.fixture
    def fetch(self):
        return Fetch(cache={"name":"test-cache", "backend": "memory"})

    @pytest.fixture
    def chrome(self):
        return Fetch(cache={"name":"test-cache", "backend": "memory", "allowable_methods": ["GET", "HEAD", "POST"]}, browser="chrome")

    @pytest.fixture
    def fetch_force_cache(self):
        return Fetch(cache={"name":"test-cache", "backend": "memory", "allowable_methods": ["GET", "HEAD", "POST"], "allowable_codes": [200, 302]})

    def test_requests_cache(self, fetch):
        url = "https://httpbin.org" + '/get'
        res = fetch.request("GET", url=url)
        assert res.status_code == 200
        assert res.url == url
        assert isinstance(res, OriginalResponse)

        # check the cache
        assert fetch.cache.contains(url=url)

        # make the same request and validate it didn't hit the cache
        res = fetch.request("GET", url=url)
        assert res.status_code == 200
        assert res.url == url
        assert isinstance(res, CachedResponse)

    def test_default_cache_ignores_post(self, fetch):
        url = "https://httpbin.org" + '/post'
        res = fetch.request("POST", url="https://httpbin.org".url + '/post')
        assert res.status_code == 200
        assert res.url == "https://httpbin.org".url + '/post'
        assert isinstance(res, OriginalResponse)

    def test_cache_with_post_allowed(self, fetch_force_cache):
        url = "https://httpbin.org" + "/post"
        assert not fetch_force_cache.cache.contains(url=url)
        res = fetch_force_cache.request("POST", url=url)
        assert res.status_code == 200
        assert res.url == url
        assert isinstance(res, OriginalResponse)

        assert url in fetch_force_cache.cache.urls()
        # assert fetch_force_cache.cache.contains(url=url)
        # make the same request and validate it hit the cache
        res = fetch_force_cache.request("POST", url=url)
        assert res.status_code == 200
        assert res.url == url
        assert isinstance(res, CachedResponse)

    def test_chrome_request(self, chrome, fetch):
        url = "https://httpbin.org" + '/headers'
        res = chrome.request("GET", url=url)
        assert res.status_code == 200
        assert res.url == url
        assert isinstance(res, OriginalResponse)

        r = res.json()
        assert "Chrome/" in r['headers']['User-Agent']
        assert chrome.cache.contains(url=url)

        # # make the same request and validate it hit the cache
        res = chrome.request("GET", url=url)
        assert res.status_code == 200
        assert res.url == url
        assert isinstance(res, CachedResponse)

    def test_chrome_no_cache(self, chrome):
        url = "https://httpbin.org" + '/get'
        res = chrome.request("GET", url=url, cache=False)
        assert res.status_code == 200
        assert res.url == url
        assert isinstance(res, RequestsResponse)


    def test_encoding_cache(self, chrome):
        formats = ['brotli', 'deflate', 'gzip', 'json',]
        for response_format in formats:
            url = "https://httpbin.org" + f'/{response_format}'
            response = chrome.request("GET", url=url, cache=True)
            assert response.status_code == 200
            assert chrome.cache.contains(url=url)
            d = response.json()
            assert isinstance(d, dict)

            # make the same request again
            response = chrome.request("GET", url=url, cache=True)
            assert isinstance(response, CachedResponse)

    def test_post_cache(self, chrome):
        url = "https://httpbin.org" + '/anything'
        data = {"key": "value"}
        request = PreparedRequest()
        request.prepare(json=data, url=url)
        request.method = "POST"
        response = chrome.request("POST", url=url, json=data, cache=True)
        assert response.status_code == 200
        assert chrome.cache.contains(request=request)
        assert isinstance(response.json(), dict)

    def test_cookies(self, chrome):
        url = "https://httpbin.org" + "/cookies/set/test/cookie"
        response = chrome.request("GET", url=url, cache=True)
        print(response)
        assert response.status_code == 200
        assert chrome.cache.contains(url=url)
        assert response.json()['cookies']['test'] == 'cookie'

        cookie = list(response.cookies)[0]
        assert cookie.name == 'test'
        assert cookie.value == 'cookie'
        assert cookie.port == None
