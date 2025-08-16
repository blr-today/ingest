from curl_cffi import requests as curl
from requests_cache import CachedSession
from requests_cache import CacheActions
from requests_cache.models import (
    AnyResponse,
    CachedResponse,
    OriginalResponse,
    AnyRequest,
    CachedRequest,
)
from requests.models import PreparedRequest
from .response import CorrectResponse
from io import BytesIO

from datetime import timedelta


def get_cached_session(
    cache_name="event-fetcher-cache",
    days=1,
    allowable_codes=(200,),
    allowable_methods=["GET"],
    backend="sqlite",
    serializer=None,
):
    """
    Initializes and returns a CachedSession instance with common settings.
    """
    session = CachedSession(
        cache_name=cache_name,
        expire_after=timedelta(days=days),
        stale_if_error=True,
        use_cache_dir=True,
        cache_control=False,
        allowable_codes=allowable_codes,
        allowable_methods=allowable_methods,
        backend=backend,
        serializer=serializer,
    )
    return session


class Fetch:
    def __init__(self, cache={}, browser=None):
        self.session = get_cached_session(
            cache.get("name", "event-fetcher-cache"),
            cache.get("days", 1),
            cache.get("allowable_codes", (200, 302, 307)),
            cache.get("allowable_methods", ["GET", "HEAD", "POST"]),
            cache.get("backend", "sqlite"),
            cache.get("serializer", None),
        )
        self.cache = self.session.cache
        self.curl = curl.session
        self.browser = browser

    def head(self, url, **kwargs):
        return self.request("HEAD", url=url, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url=url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url=url, **kwargs)

    def _send_and_cache(
        self, request: PreparedRequest, actions: CacheActions, cached_response=None
    ) -> AnyResponse:
        """Send a request and cache the response, unless disabled by settings or headers.
        If applicable, also handle conditional requests.
        """
        request = actions.update_request(request)
        response = curl.request(
            method=request.method,
            url=request.url,
            headers=request.headers,
            data=request.body,
            impersonate=self.browser,
        )

        response = CorrectResponse(request, response)
        actions.update_from_response(response)

        if not actions.skip_write:
            self.cache.save_response(response, actions.cache_key, actions.expires)
        else:
            logger.debug(f"Skipping cache write for URL: {request.url}")

        # This is possible if the original request is a cache miss, but updating its validation
        # headers results in redirecting to a different URL that is a cache hit
        if isinstance(response, CachedResponse):
            return response
        else:
            return OriginalResponse.wrap_response(response, actions)

    def request(self, method, cache=True, **kwargs):
        if self.browser:
            # TODO: How to set cookies?
            pr = PreparedRequest()
            pr.prepare(**kwargs)
            pr.method = method

            if cache:
                request = CachedRequest.from_request(pr)
                actions = CacheActions.from_request(
                    self.cache.create_key(request), request, self.cache._settings
                )
                cached_response: Optional[CachedResponse] = None
                if not actions.skip_read:
                    cached_response = self.cache.get_response(actions.cache_key)

                actions.update_from_cached_response(
                    cached_response, self.cache.create_key, **kwargs
                )

                if actions.resend_request or actions.send_request:
                    return self._send_and_cache(pr, actions, cached_response)
                return cached_response
            else:
                print("Fetching using CURL")
                response = curl.request(
                    method=method, impersonate=self.browser, **kwargs
                )
                return CorrectResponse(pr, response)
        elif cache == True:
            return self.session.request(method, **kwargs)
        with self.session.cache_disabled():
            return self.session.request(method, **kwargs)
