import pytest
import responses

from notesearch.gemini import API_BASE, DEFAULT_MODEL, GeminiError, ask, load_api_key


def test_load_api_key_from_config():
    assert load_api_key({"gemini_api_key": "from-config"}) == "from-config"


def test_load_api_key_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert load_api_key(None) == "from-env"


def test_load_api_key_config_takes_priority_over_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert load_api_key({"gemini_api_key": "from-config"}) == "from-config"


def test_load_api_key_missing_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(GeminiError):
        load_api_key(None)


@responses.activate
def test_ask_sends_prompt_and_returns_text():
    responses.add(
        responses.POST,
        f"{API_BASE}/{DEFAULT_MODEL}:generateContent",
        json={"candidates": [{"content": {"parts": [{"text": "This is the answer."}]}}]},
        status=200,
    )
    result = ask("What is Docker?", api_key="test-key")
    assert result == "This is the answer."


@responses.activate
def test_ask_includes_api_key_in_url():
    responses.add(
        responses.POST,
        f"{API_BASE}/{DEFAULT_MODEL}:generateContent",
        json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
        status=200,
    )
    ask("question", api_key="my-secret-key")
    assert "key=my-secret-key" in responses.calls[0].request.url


@responses.activate
def test_ask_sends_prompt_in_request_body():
    responses.add(
        responses.POST,
        f"{API_BASE}/{DEFAULT_MODEL}:generateContent",
        json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
        status=200,
    )
    ask("my exact question text", api_key="key")
    import json

    body = json.loads(responses.calls[0].request.body)
    assert body["contents"][0]["parts"][0]["text"] == "my exact question text"


@responses.activate
def test_ask_unexpected_response_shape_raises_gemini_error():
    responses.add(
        responses.POST,
        f"{API_BASE}/{DEFAULT_MODEL}:generateContent",
        json={"unexpected": "shape"},
        status=200,
    )
    with pytest.raises(GeminiError):
        ask("question", api_key="key")


@responses.activate
def test_ask_http_error_raises():
    responses.add(
        responses.POST,
        f"{API_BASE}/{DEFAULT_MODEL}:generateContent",
        json={"error": "bad request"},
        status=400,
    )
    with pytest.raises(Exception):
        ask("question", api_key="key")


@responses.activate
def test_ask_custom_model():
    responses.add(
        responses.POST,
        f"{API_BASE}/gemini-1.5-pro:generateContent",
        json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]},
        status=200,
    )
    result = ask("question", api_key="key", model="gemini-1.5-pro")
    assert result == "ok"
