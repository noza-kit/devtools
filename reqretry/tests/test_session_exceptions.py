from __future__ import annotations

import pytest
import requests
import responses

from reqretry import RetryConfig, Session

URL = "https://example.test/api"


@responses.activate
def test_retries_connection_error_then_succeeds(session, no_sleep):
    responses.add(responses.GET, URL, body=requests.exceptions.ConnectionError())
    responses.add(responses.GET, URL, status=200, body="ok")

    resp = session.get(URL)

    assert resp.status_code == 200
    assert no_sleep == [1.0]


@responses.activate
def test_retries_timeout_then_succeeds(session, no_sleep):
    responses.add(responses.GET, URL, body=requests.exceptions.Timeout())
    responses.add(responses.GET, URL, body=requests.exceptions.Timeout())
    responses.add(responses.GET, URL, status=200, body="ok")

    resp = session.get(URL)

    assert resp.status_code == 200
    assert no_sleep == [1.0, 2.0]


@responses.activate
def test_raises_after_exhausting_retries(no_sleep):
    config = RetryConfig(max_retries=2, backoff_factor=0.01, backoff_multiplier=2.0)
    session = Session(config)
    for _ in range(3):  # 1 initial attempt + 2 retries, all fail
        responses.add(responses.GET, URL, body=requests.exceptions.ConnectionError())

    with pytest.raises(requests.exceptions.ConnectionError):
        session.get(URL)

    assert no_sleep == [0.01, 0.02]


@responses.activate
def test_non_retried_exception_propagates_immediately(no_sleep):
    responses.add(responses.GET, URL, body=ValueError("not a retryable failure"))

    with pytest.raises(ValueError):
        session_ = Session(RetryConfig())
        session_.get(URL)

    assert no_sleep == []
