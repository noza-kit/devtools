from __future__ import annotations

import responses

import reqretry

URL = "https://example.test/api"


@responses.activate
def test_module_get_delegates_to_default_session(no_sleep):
    responses.add(responses.GET, URL, status=200, body="ok")

    resp = reqretry.get(URL)

    assert resp.status_code == 200
    assert resp.text == "ok"


@responses.activate
def test_module_post_delegates_to_default_session(no_sleep):
    responses.add(responses.POST, URL, status=201, json={"created": True})

    resp = reqretry.post(URL, json={"x": 1})

    assert resp.status_code == 201
    assert resp.json() == {"created": True}


@responses.activate
def test_configure_updates_default_session_retry_behavior(no_sleep):
    reqretry.configure(max_retries=1, backoff_factor=0.25)
    responses.add(responses.GET, URL, status=503)
    responses.add(responses.GET, URL, status=200)

    resp = reqretry.get(URL)

    assert resp.status_code == 200
    assert no_sleep == [0.25]


def test_configure_returns_updated_config():
    config = reqretry.configure(max_retries=9)
    assert config.max_retries == 9
    assert config is reqretry.get_default_session().retry_config
