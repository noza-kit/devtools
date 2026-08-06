from __future__ import annotations

import os
from typing import Any, Mapping, Optional

import reqretry

DEFAULT_MODEL = "gemini-2.0-flash"
API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiError(Exception):
    pass


def load_api_key(config: Optional[Mapping[str, Any]] = None) -> str:
    """Resolve the Gemini API key: `config["gemini_api_key"]` first,
    then the GEMINI_API_KEY env var. `config` may be a plain dict or a
    confload.Config."""
    if config is not None:
        try:
            value = config["gemini_api_key"]
            if value:
                return value
        except KeyError:
            pass

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise GeminiError("GEMINI_API_KEY is not set (env var or config)")
    return key


def ask(
    prompt: str,
    api_key: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    config: Optional[Mapping[str, Any]] = None,
    timeout: float = 60.0,
) -> str:
    """Send `prompt` (typically notesearch's own RAG-formatted prompt,
    with a real question in place of the placeholder) to the Gemini API
    and return its text answer."""
    key = api_key or load_api_key(config)
    url = f"{API_BASE}/{model}:generateContent?key={key}"
    response = reqretry.post(
        url,
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GeminiError(f"unexpected Gemini API response shape: {data}") from exc
