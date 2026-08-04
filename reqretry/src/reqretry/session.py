from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from reqretry.config import RetryConfig

logger = logging.getLogger("reqretry")


class Session:
    """Wraps a requests.Session with configurable retry/backoff and a default timeout."""

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        *,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.retry_config = retry_config or RetryConfig()
        self._session = session or requests.Session()

    def request(
        self,
        method: str,
        url: str,
        *,
        retry_config: Optional[RetryConfig] = None,
        **kwargs,
    ) -> requests.Response:
        config = retry_config or self.retry_config
        if kwargs.get("timeout") is None:
            # Also overrides an explicit timeout=None: requests treats that as "wait
            # forever", which is exactly the hang this default exists to prevent.
            kwargs["timeout"] = config.timeout

        wait = config.backoff_factor
        attempt = 0
        while True:
            try:
                response = self._session.request(method, url, **kwargs)
            except config.retry_exceptions as exc:
                if attempt >= config.max_retries:
                    raise
                attempt += 1
                logger.warning(
                    "%s %s failed (%s: %s); retry %d/%d in %.1fs",
                    method.upper(), url, type(exc).__name__, exc, attempt, config.max_retries, wait,
                )
                time.sleep(wait)
                wait *= config.backoff_multiplier
                continue

            if response.status_code in config.retry_status_codes and attempt < config.max_retries:
                attempt += 1
                logger.warning(
                    "%s %s returned %d; retry %d/%d in %.1fs",
                    method.upper(), url, response.status_code, attempt, config.max_retries, wait,
                )
                time.sleep(wait)
                wait *= config.backoff_multiplier
                continue

            return response

    def get(self, url: str, **kwargs) -> requests.Response:
        return self.request("GET", url, **kwargs)

    def options(self, url: str, **kwargs) -> requests.Response:
        return self.request("OPTIONS", url, **kwargs)

    def head(self, url: str, **kwargs) -> requests.Response:
        kwargs.setdefault("allow_redirects", False)
        return self.request("HEAD", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> requests.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs) -> requests.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs) -> requests.Response:
        return self.request("DELETE", url, **kwargs)

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()
