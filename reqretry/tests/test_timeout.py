from __future__ import annotations

import responses

from reqretry import RetryConfig, Session

URL = "https://example.test/api"


@responses.activate
def test_default_timeout_applied_when_omitted(no_sleep):
    session = Session(RetryConfig(timeout=7.5))
    responses.add(responses.GET, URL, status=200)

    session.get(URL)

    assert responses.calls[0].request.req_kwargs["timeout"] == 7.5


@responses.activate
def test_explicit_timeout_is_preserved(no_sleep):
    session = Session(RetryConfig(timeout=7.5))
    responses.add(responses.GET, URL, status=200)

    session.get(URL, timeout=1.0)

    assert responses.calls[0].request.req_kwargs["timeout"] == 1.0


@responses.activate
def test_explicit_timeout_none_still_gets_default(no_sleep):
    """timeout=None means 'wait forever' in requests -- the default exists to prevent that hang."""
    session = Session(RetryConfig(timeout=7.5))
    responses.add(responses.GET, URL, status=200)

    session.get(URL, timeout=None)

    assert responses.calls[0].request.req_kwargs["timeout"] == 7.5
