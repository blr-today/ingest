from requests_cache import CachedSession
from datetime import timedelta

def get_cached_session(cache_name='event-fetcher-cache', days=1, allowable_codes=(200,), allowable_methods=["GET"]):
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
    )
    return session
