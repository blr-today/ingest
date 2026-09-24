import requests_cache.backends.base as _rc_base
from cattrs.errors import BaseValidationError

USER_AGENT_HEADERS = {
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0 blr-today-fetcher/0 (+https://blr.today/docs/bots)"
}

# cattrs wraps corrupt cache rows in errors requests-cache misses; treat as cache miss
_rc_base.DESERIALIZE_ERRORS += (BaseValidationError,)
