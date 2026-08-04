from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple, Union

import requests

#: Status codes retried by default: the whole 5xx class (server-side failures).
DEFAULT_RETRY_STATUS_CODES = frozenset(range(500, 600))

#: Exceptions retried by default: connection failures and timeouts.
DEFAULT_RETRY_EXCEPTIONS: Tuple[type, ...] = (
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)

#: Timeout (seconds, or (connect, read) tuple) applied when a call omits one.
DEFAULT_TIMEOUT: Union[float, Tuple[float, float]] = 10.0


@dataclass
class RetryConfig:
    """Controls retry/backoff/timeout behavior for a Session or a single call."""

    max_retries: int = 3
    backoff_factor: float = 1.0
    backoff_multiplier: float = 2.0
    retry_status_codes: frozenset = field(default_factory=lambda: DEFAULT_RETRY_STATUS_CODES)
    retry_exceptions: Tuple[type, ...] = DEFAULT_RETRY_EXCEPTIONS
    timeout: Union[float, Tuple[float, float]] = DEFAULT_TIMEOUT

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if self.backoff_factor < 0:
            raise ValueError("backoff_factor must be >= 0")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be >= 1")
