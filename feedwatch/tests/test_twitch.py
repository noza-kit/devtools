from __future__ import annotations

import pytest
import responses

from feedwatch.twitch import (
    STREAMS_URL,
    TOKEN_URL,
    TwitchAPIError,
    TwitchClient,
    TwitchConfigError,
    load_credentials,
)


def test_load_credentials_from_env(monkeypatch):
    monkeypatch.setenv("TWITCH_CLIENT_ID", "cid")
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "secret")

    assert load_credentials() == ("cid", "secret")


def test_load_credentials_missing_raises(monkeypatch):
    monkeypatch.delenv("TWITCH_CLIENT_ID", raising=False)
    monkeypatch.delenv("TWITCH_CLIENT_SECRET", raising=False)

    with pytest.raises(TwitchConfigError):
        load_credentials()


def test_load_credentials_from_config_object(monkeypatch):
    monkeypatch.delenv("TWITCH_CLIENT_ID", raising=False)
    monkeypatch.delenv("TWITCH_CLIENT_SECRET", raising=False)
    config = {"twitch_client_id": "cid2", "twitch_client_secret": "secret2"}

    assert load_credentials(config) == ("cid2", "secret2")


@responses.activate
def test_get_live_stream_returns_stream_info(no_sleep):
    responses.add(responses.POST, TOKEN_URL, json={"access_token": "tok123", "expires_in": 3600}, status=200)
    responses.add(
        responses.GET,
        STREAMS_URL,
        json={
            "data": [
                {"id": "stream1", "title": "Playing games", "user_name": "SomeStreamer", "user_login": "somestreamer"}
            ]
        },
        status=200,
    )

    client = TwitchClient("cid", "secret")
    stream = client.get_live_stream("somestreamer")

    assert stream is not None
    assert stream.stream_id == "stream1"
    assert stream.title == "Playing games"
    assert stream.url == "https://www.twitch.tv/somestreamer"
    assert responses.calls[1].request.headers["Client-Id"] == "cid"
    assert responses.calls[1].request.headers["Authorization"] == "Bearer tok123"


@responses.activate
def test_get_live_stream_offline_returns_none(no_sleep):
    responses.add(responses.POST, TOKEN_URL, json={"access_token": "tok123"}, status=200)
    responses.add(responses.GET, STREAMS_URL, json={"data": []}, status=200)

    client = TwitchClient("cid", "secret")

    assert client.get_live_stream("somestreamer") is None


@responses.activate
def test_get_live_stream_reuses_cached_token(no_sleep):
    responses.add(responses.POST, TOKEN_URL, json={"access_token": "tok123"}, status=200)
    responses.add(responses.GET, STREAMS_URL, json={"data": []}, status=200)
    responses.add(responses.GET, STREAMS_URL, json={"data": []}, status=200)

    client = TwitchClient("cid", "secret")
    client.get_live_stream("a")
    client.get_live_stream("b")

    token_calls = [c for c in responses.calls if c.request.url.startswith(TOKEN_URL)]
    assert len(token_calls) == 1


@responses.activate
def test_get_live_stream_refreshes_token_on_401(no_sleep):
    responses.add(responses.POST, TOKEN_URL, json={"access_token": "tok1"}, status=200)
    responses.add(responses.GET, STREAMS_URL, status=401)
    responses.add(responses.POST, TOKEN_URL, json={"access_token": "tok2"}, status=200)
    responses.add(
        responses.GET,
        STREAMS_URL,
        json={"data": [{"id": "s1", "title": "t", "user_name": "u", "user_login": "u"}]},
        status=200,
    )

    client = TwitchClient("cid", "secret")
    stream = client.get_live_stream("u")

    assert stream.stream_id == "s1"
    assert responses.calls[-1].request.headers["Authorization"] == "Bearer tok2"


@responses.activate
def test_get_live_stream_api_error_raises(no_sleep):
    responses.add(responses.POST, TOKEN_URL, json={"access_token": "tok1"}, status=200)
    for _ in range(4):  # reqretry default: 1 initial attempt + 3 retries, all 500
        responses.add(responses.GET, STREAMS_URL, status=500)

    client = TwitchClient("cid", "secret")

    with pytest.raises(TwitchAPIError):
        client.get_live_stream("u")
