from __future__ import annotations

import responses

from reqretry import RetryConfig, Session

URL = "https://example.test/api"


@responses.activate
def test_success_on_first_try_does_not_retry(session, no_sleep):
    responses.add(responses.GET, URL, status=200, body="ok")

    resp = session.get(URL)

    assert resp.status_code == 200
    assert no_sleep == []


@responses.activate
def test_retries_5xx_then_succeeds(session, no_sleep):
    responses.add(responses.GET, URL, status=503)
    responses.add(responses.GET, URL, status=503)
    responses.add(responses.GET, URL, status=200, body="ok")

    resp = session.get(URL)

    assert resp.status_code == 200
    assert resp.text == "ok"
    # default backoff_factor=1.0, backoff_multiplier=2.0 -> 1s, then 2s
    assert no_sleep == [1.0, 2.0]


@responses.activate
def test_exhausts_retries_and_returns_last_response(no_sleep):
    config = RetryConfig(max_retries=2, backoff_factor=0.01, backoff_multiplier=2.0)
    session = Session(config)
    for _ in range(3):  # 1 initial attempt + 2 retries
        responses.add(responses.GET, URL, status=500)

    resp = session.get(URL)

    assert resp.status_code == 500
    assert no_sleep == [0.01, 0.02]


@responses.activate
def test_non_retry_status_returned_immediately(session, no_sleep):
    responses.add(responses.GET, URL, status=404)

    resp = session.get(URL)

    assert resp.status_code == 404
    assert no_sleep == []


@responses.activate
def test_custom_retry_status_codes(no_sleep):
    config = RetryConfig(max_retries=2, backoff_factor=0.01, retry_status_codes=frozenset({429}))
    session = Session(config)
    responses.add(responses.GET, URL, status=500)  # not in custom set -> returned as-is

    resp = session.get(URL)

    assert resp.status_code == 500
    assert no_sleep == []


@responses.activate
def test_per_call_retry_config_overrides_session_default(no_sleep):
    session = Session(RetryConfig(max_retries=3, backoff_factor=0.01))
    responses.add(responses.GET, URL, status=503)

    resp = session.get(URL, retry_config=RetryConfig(max_retries=0))

    assert resp.status_code == 503
    assert no_sleep == []


@responses.activate
def test_max_retries_zero_disables_retry(no_sleep):
    session = Session(RetryConfig(max_retries=0))
    responses.add(responses.GET, URL, status=503)

    resp = session.get(URL)

    assert resp.status_code == 503
    assert no_sleep == []
