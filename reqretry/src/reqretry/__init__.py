from __future__ import annotations

from dataclasses import replace
from typing import Any

import requests

from reqretry.config import RetryConfig
from reqretry.session import Session

__version__ = "0.1.0"

__all__ = [
    "RetryConfig",
    "Session",
    "configure",
    "get_default_session",
    "request",
    "get",
    "options",
    "head",
    "post",
    "put",
    "patch",
    "delete",
]

_default_session = Session()


def get_default_session() -> Session:
    """The Session backing the module-level get/post/etc. functions."""
    return _default_session


def configure(**kwargs: Any) -> RetryConfig:
    """Update the default session's RetryConfig in place (e.g. configure(max_retries=5))."""
    _default_session.retry_config = replace(_default_session.retry_config, **kwargs)
    return _default_session.retry_config


def request(method: str, url: str, **kwargs) -> requests.Response:
    return _default_session.request(method, url, **kwargs)


def get(url: str, **kwargs) -> requests.Response:
    return _default_session.get(url, **kwargs)


def options(url: str, **kwargs) -> requests.Response:
    return _default_session.options(url, **kwargs)


def head(url: str, **kwargs) -> requests.Response:
    return _default_session.head(url, **kwargs)


def post(url: str, **kwargs) -> requests.Response:
    return _default_session.post(url, **kwargs)


def put(url: str, **kwargs) -> requests.Response:
    return _default_session.put(url, **kwargs)


def patch(url: str, **kwargs) -> requests.Response:
    return _default_session.patch(url, **kwargs)


def delete(url: str, **kwargs) -> requests.Response:
    return _default_session.delete(url, **kwargs)
