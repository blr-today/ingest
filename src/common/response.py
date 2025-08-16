# SRC: https://github.com/paivett/requests-curl/
# Public-Domain

from curl_cffi.requests.models import Response as CURLResponse
from http.client import parse_headers
from requests import Response as RequestResponse
from requests.models import PreparedRequest
from requests.utils import get_encoding_from_headers
from requests.structures import CaseInsensitiveDict
from requests.cookies import RequestsCookieJar
from urllib3.response import HTTPResponse as URLLib3Rresponse
from io import BytesIO


class CorrectResponse(RequestResponse):
    def __init__(self, request: PreparedRequest, response: CURLResponse):
        super().__init__()

        self.status_code = response.status_code
        self.reason = response.reason
        self.body = BytesIO(response.content)
        self.method = request.method
        self.body.seek(0)
        self.request = request
        self.raw = BytesIO(response.content)
        self.raw._request_url = None
        self.reason = response.reason
        self.headers = response.headers
        self.cookies = RequestsCookieJar()
        self.cookies.update(response.cookies.jar)
        self.url = response.url
