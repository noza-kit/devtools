from __future__ import annotations

import pytest
import requests

from reqretry import RetryConfig


def test_defaults_match_spec():
    config = RetryConfig()
    assert config.max_retries == 3
    assert config.backoff_factor == 1.0
    assert config.backoff_multiplier == 2.0
    assert config.timeout == 10.0
    assert 500 in config.retry_status_codes
    assert 599 in config.retry_status_codes
    assert 404 not in config.retry_status_codes
    assert requests.exceptions.Timeout in config.retry_exceptions
    assert requests.exceptions.ConnectionError in config.retry_exceptions


def test_fields_are_overridable():
    config = RetryConfig(
        max_retries=5,
        backoff_factor=0.1,
        backoff_multiplier=3.0,
        retry_status_codes=frozenset({429}),
        timeout=2.5,
    )
    assert config.max_retries == 5
    assert config.retry_status_codes == frozenset({429})
    assert config.timeout == 2.5


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_retries": -1},
        {"backoff_factor": -0.5},
        {"backoff_multiplier": 0.5},
    ],
)
def test_invalid_values_rejected(kwargs):
    with pytest.raises(ValueError):
        RetryConfig(**kwargs)
