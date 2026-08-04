from __future__ import annotations

import json

import pytest
import responses

from translate_comments.deepl_client import (
    DEEPL_FREE_URL,
    DEEPL_PRO_URL,
    DeepLClient,
    DeepLConfigError,
    DeepLError,
    load_api_key,
)

API_KEY = "test-key-123"
FREE_API_KEY = "test-key-456:fx"


# --- load_api_key -----------------------------------------------------------------


def test_load_api_key_from_env(monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", API_KEY)

    assert load_api_key() == API_KEY


def test_load_api_key_from_config_takes_precedence(monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", "env-key")

    assert load_api_key({"deepl_api_key": "config-key"}) == "config-key"


def test_load_api_key_falls_back_to_env_when_config_lacks_key(monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", API_KEY)

    assert load_api_key({"other": "value"}) == API_KEY


def test_load_api_key_missing_raises(monkeypatch):
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)

    with pytest.raises(DeepLConfigError):
        load_api_key()


# --- DeepLClient construction -------------------------------------------------------


def test_empty_api_key_raises():
    with pytest.raises(DeepLConfigError):
        DeepLClient(api_key="")


def test_free_tier_key_uses_free_host():
    client = DeepLClient(api_key=FREE_API_KEY)
    assert client.base_url == DEEPL_FREE_URL


def test_pro_key_uses_pro_host():
    client = DeepLClient(api_key=API_KEY)
    assert client.base_url == DEEPL_PRO_URL


# --- translate() --------------------------------------------------------------------


@responses.activate
def test_translate_success(no_sleep):
    responses.add(
        responses.POST,
        DEEPL_PRO_URL,
        json={"translations": [{"text": "Hello world"}, {"text": "Goodbye"}]},
        status=200,
    )

    client = DeepLClient(api_key=API_KEY)
    result = client.translate(["こんにちは世界", "さようなら"], source_lang="ja", target_lang="en")

    assert result == ["Hello world", "Goodbye"]

    request = responses.calls[0].request
    assert request.headers["Authorization"] == f"DeepL-Auth-Key {API_KEY}"
    body = request.body if isinstance(request.body, str) else request.body.decode()
    assert "source_lang=JA" in body
    assert "target_lang=EN-US" in body


@responses.activate
def test_translate_empty_input_makes_no_request(no_sleep):
    client = DeepLClient(api_key=API_KEY)

    assert client.translate([], source_lang="ja", target_lang="en") == []
    assert len(responses.calls) == 0


def test_translate_unsupported_source_lang_raises_without_request():
    client = DeepLClient(api_key=API_KEY)

    with pytest.raises(DeepLConfigError):
        client.translate(["hi"], source_lang="de", target_lang="en")


def test_translate_unsupported_target_lang_raises_without_request():
    client = DeepLClient(api_key=API_KEY)

    with pytest.raises(DeepLConfigError):
        client.translate(["hi"], source_lang="ja", target_lang="de")


@responses.activate
def test_translate_error_response_raises(no_sleep):
    responses.add(responses.POST, DEEPL_PRO_URL, status=456, body="quota exceeded")

    client = DeepLClient(api_key=API_KEY)
    with pytest.raises(DeepLError):
        client.translate(["hi"], source_lang="ja", target_lang="en")


@responses.activate
def test_translate_retries_on_429_then_succeeds(no_sleep):
    responses.add(responses.POST, DEEPL_PRO_URL, status=429)
    responses.add(
        responses.POST, DEEPL_PRO_URL, json={"translations": [{"text": "Hello"}]}, status=200
    )

    client = DeepLClient(api_key=API_KEY)
    result = client.translate(["こんにちは"], source_lang="ja", target_lang="en")

    assert result == ["Hello"]
    assert no_sleep == [1.0]


@responses.activate
def test_translate_connection_error_raises_deepl_error(no_sleep):
    import requests

    responses.add(responses.POST, DEEPL_PRO_URL, body=requests.exceptions.ConnectionError())
    responses.add(responses.POST, DEEPL_PRO_URL, body=requests.exceptions.ConnectionError())
    responses.add(responses.POST, DEEPL_PRO_URL, body=requests.exceptions.ConnectionError())
    responses.add(responses.POST, DEEPL_PRO_URL, body=requests.exceptions.ConnectionError())

    client = DeepLClient(api_key=API_KEY)
    with pytest.raises(DeepLError):
        client.translate(["hi"], source_lang="ja", target_lang="en")


# --- translate_to_many() -------------------------------------------------------------


@responses.activate
def test_translate_to_many_calls_api_once_per_target(no_sleep):
    responses.add(
        responses.POST, DEEPL_PRO_URL, json={"translations": [{"text": "Hello"}]}, status=200
    )
    responses.add(
        responses.POST, DEEPL_PRO_URL, json={"translations": [{"text": "Bonjour"}]}, status=200
    )

    client = DeepLClient(api_key=API_KEY)
    result = client.translate_to_many(["こんにちは"], source_lang="ja", target_langs=["en", "fr"])

    assert result == {"en": ["Hello"], "fr": ["Bonjour"]}
    assert len(responses.calls) == 2
