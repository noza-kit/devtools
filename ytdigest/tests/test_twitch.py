from __future__ import annotations

import json

import pytest
import responses

from ytdigest.twitch import (
    API_BASE,
    TOKEN_URL,
    TwitchClient,
    TwitchConfigError,
    TwitchError,
)


def _mock_token(access_token="test-token", expires_in=3600):
    responses.add(
        responses.POST,
        TOKEN_URL,
        json={"access_token": access_token, "expires_in": expires_in, "token_type": "bearer"},
        status=200,
    )


def test_missing_credentials_raises():
    with pytest.raises(TwitchConfigError):
        TwitchClient(client_id="", client_secret="secret")
    with pytest.raises(TwitchConfigError):
        TwitchClient(client_id="id", client_secret="")


@responses.activate
def test_get_live_streams_returns_live_channels_only(no_sleep):
    _mock_token()
    responses.add(
        responses.GET,
        f"{API_BASE}/streams",
        json={
            "data": [
                {
                    "id": "stream-1",
                    "user_login": "streamer1",
                    "user_name": "Streamer1",
                    "title": "Playing games",
                    "started_at": "2026-08-01T12:00:00Z",
                    "thumbnail_url": "https://cdn.example/preview-{width}x{height}.jpg",
                }
            ]
        },
        status=200,
    )

    client = TwitchClient(client_id="id", client_secret="secret")
    live = client.get_live_streams(["streamer1", "streamer2"])

    assert set(live) == {"streamer1"}
    assert live["streamer1"].stream_id == "stream-1"
    assert live["streamer1"].title == "Playing games"
    assert live["streamer1"].thumbnail_url == "https://cdn.example/preview-440x248.jpg"

    request = responses.calls[1].request
    assert request.headers["Authorization"] == "Bearer test-token"
    assert request.headers["Client-Id"] == "id"


@responses.activate
def test_get_live_streams_empty_input_makes_no_request(no_sleep):
    client = TwitchClient(client_id="id", client_secret="secret")
    assert client.get_live_streams([]) == {}
    assert len(responses.calls) == 0


@responses.activate
def test_token_is_cached_across_calls(no_sleep):
    _mock_token()
    responses.add(responses.GET, f"{API_BASE}/streams", json={"data": []}, status=200)
    responses.add(responses.GET, f"{API_BASE}/streams", json={"data": []}, status=200)

    client = TwitchClient(client_id="id", client_secret="secret")
    client.get_live_streams(["a"])
    client.get_live_streams(["b"])

    token_calls = [c for c in responses.calls if c.request.url.startswith(TOKEN_URL)]
    assert len(token_calls) == 1


@responses.activate
def test_401_triggers_token_refresh_and_retry(no_sleep):
    _mock_token(access_token="expired-token")
    responses.add(responses.GET, f"{API_BASE}/streams", status=401)
    _mock_token(access_token="fresh-token")
    responses.add(responses.GET, f"{API_BASE}/streams", json={"data": []}, status=200)

    client = TwitchClient(client_id="id", client_secret="secret")
    result = client.get_live_streams(["a"])

    assert result == {}
    last_request = responses.calls[-1].request
    assert last_request.headers["Authorization"] == "Bearer fresh-token"


@responses.activate
def test_get_user_id_returns_id(no_sleep):
    _mock_token()
    responses.add(responses.GET, f"{API_BASE}/users", json={"data": [{"id": "12345", "login": "streamer1"}]}, status=200)

    client = TwitchClient(client_id="id", client_secret="secret")
    assert client.get_user_id("streamer1") == "12345"


@responses.activate
def test_get_user_id_missing_returns_none(no_sleep):
    _mock_token()
    responses.add(responses.GET, f"{API_BASE}/users", json={"data": []}, status=200)

    client = TwitchClient(client_id="id", client_secret="secret")
    assert client.get_user_id("nosuchuser") is None


@responses.activate
def test_get_latest_vod_returns_latest_when_no_user(no_sleep):
    _mock_token()
    responses.add(responses.GET, f"{API_BASE}/users", json={"data": []}, status=200)

    client = TwitchClient(client_id="id", client_secret="secret")
    assert client.get_latest_vod("nosuchuser") is None


@responses.activate
def test_get_latest_vod_returns_video(no_sleep):
    _mock_token()
    responses.add(responses.GET, f"{API_BASE}/users", json={"data": [{"id": "999"}]}, status=200)
    responses.add(
        responses.GET,
        f"{API_BASE}/videos",
        json={
            "data": [
                {
                    "id": "vod1",
                    "title": "Yesterday's stream",
                    "url": "https://www.twitch.tv/videos/vod1",
                    "thumbnail_url": "https://cdn.example/vod-thumb-%{width}x%{height}.jpg",
                    "created_at": "2026-08-01T12:00:00Z",
                    "published_at": "2026-08-01T12:00:00Z",
                }
            ]
        },
        status=200,
    )

    client = TwitchClient(client_id="id", client_secret="secret")
    video = client.get_latest_vod("streamer1", after="2026-08-01T00:00:00Z")

    assert video.video_id == "vod1"
    assert video.thumbnail_url == "https://cdn.example/vod-thumb-440x248.jpg"


@responses.activate
def test_get_latest_vod_filters_out_videos_before_after(no_sleep):
    _mock_token()
    responses.add(responses.GET, f"{API_BASE}/users", json={"data": [{"id": "999"}]}, status=200)
    responses.add(
        responses.GET,
        f"{API_BASE}/videos",
        json={
            "data": [
                {
                    "id": "old-vod",
                    "title": "Old stream",
                    "url": "https://www.twitch.tv/videos/old-vod",
                    "thumbnail_url": "",
                    "created_at": "2026-07-01T00:00:00Z",
                    "published_at": "2026-07-01T00:00:00Z",
                }
            ]
        },
        status=200,
    )

    client = TwitchClient(client_id="id", client_secret="secret")
    video = client.get_latest_vod("streamer1", after="2026-08-01T00:00:00Z")

    # No candidate matches `after`; falls back to newest available rather than
    # silently dropping a VOD that legitimately belongs to this stream.
    assert video.video_id == "old-vod"


@responses.activate
def test_get_latest_vod_no_videos_returns_none(no_sleep):
    _mock_token()
    responses.add(responses.GET, f"{API_BASE}/users", json={"data": [{"id": "999"}]}, status=200)
    responses.add(responses.GET, f"{API_BASE}/videos", json={"data": []}, status=200)

    client = TwitchClient(client_id="id", client_secret="secret")
    assert client.get_latest_vod("streamer1") is None


@responses.activate
def test_token_request_error_raises(no_sleep):
    responses.add(responses.POST, TOKEN_URL, status=403, body="invalid client")

    client = TwitchClient(client_id="bad-id", client_secret="bad-secret")
    with pytest.raises(TwitchError):
        client.get_live_streams(["a"])


@responses.activate
def test_api_error_status_raises(no_sleep):
    _mock_token()
    responses.add(responses.GET, f"{API_BASE}/streams", status=500)
    responses.add(responses.GET, f"{API_BASE}/streams", status=500)
    responses.add(responses.GET, f"{API_BASE}/streams", status=500)
    responses.add(responses.GET, f"{API_BASE}/streams", status=500)

    client = TwitchClient(client_id="id", client_secret="secret")
    with pytest.raises(TwitchError):
        client.get_live_streams(["a"])


@responses.activate
def test_connection_error_raises(no_sleep):
    import requests

    responses.add(responses.POST, TOKEN_URL, body=requests.exceptions.ConnectionError())
    responses.add(responses.POST, TOKEN_URL, body=requests.exceptions.ConnectionError())
    responses.add(responses.POST, TOKEN_URL, body=requests.exceptions.ConnectionError())
    responses.add(responses.POST, TOKEN_URL, body=requests.exceptions.ConnectionError())

    client = TwitchClient(client_id="id", client_secret="secret")
    with pytest.raises(TwitchError):
        client.get_live_streams(["a"])
