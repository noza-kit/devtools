from __future__ import annotations

import logging

import requests
import responses

from reqretry import RetryConfig, Session

URL = "https://example.test/api"


@responses.activate
def test_logs_retry_count_and_wait_on_status(session, no_sleep, caplog):
    responses.add(responses.GET, URL, status=503)
    responses.add(responses.GET, URL, status=200)

    with caplog.at_level(logging.WARNING, logger="reqretry"):
        session.get(URL)

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "retry 1/3" in message
    assert "1.0s" in message
    assert "503" in message


@responses.activate
def test_logs_retry_reason_on_exception(no_sleep, caplog):
    session = Session(RetryConfig(max_retries=1, backoff_factor=0.5))
    responses.add(responses.GET, URL, body=requests.exceptions.Timeout())
    responses.add(responses.GET, URL, status=200)

    with caplog.at_level(logging.WARNING, logger="reqretry"):
        session.get(URL)

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "retry 1/1" in message
    assert "0.5s" in message
    assert "Timeout" in message
