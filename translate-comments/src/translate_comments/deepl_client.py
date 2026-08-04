from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

import reqretry
import requests

DEEPL_FREE_URL = "https://api-free.deepl.com/v2/translate"
DEEPL_PRO_URL = "https://api.deepl.com/v2/translate"

# DeepL source-language codes: a bare code works for all three.
_SOURCE_LANG = {"ja": "JA", "en": "EN", "fr": "FR"}
# DeepL target-language codes: English requires a regional variant (EN-US/EN-GB);
# EN-US is the default here since neither spec nor DeepL implies a preference.
_TARGET_LANG = {"ja": "JA", "en": "EN-US", "fr": "FR"}

SUPPORTED_LANGUAGES = frozenset(_SOURCE_LANG)

# DeepL free-tier accounts key their requests off a ":fx"-suffixed API key and
# a different host; 429 (rate limited) is retried in addition to reqretry's
# default 5xx/timeout/connection-error set.
_RETRY_STATUS_CODES = reqretry.RetryConfig().retry_status_codes | {429}


class DeepLError(Exception):
    """Raised when the DeepL API returns an error response or the request fails."""


class DeepLConfigError(DeepLError):
    """Raised for a missing API key or an unsupported language code."""


def load_api_key(config: Optional[Mapping[str, Any]] = None) -> str:
    """Resolve the DeepL API key: `config["deepl_api_key"]` first, then the
    DEEPL_API_KEY env var. `config` may be a plain dict or a confload.Config."""
    if config is not None:
        try:
            value = config["deepl_api_key"]
        except (KeyError, TypeError):
            value = None
        if value:
            return str(value)
    key = os.environ.get("DEEPL_API_KEY")
    if not key:
        raise DeepLConfigError("DEEPL_API_KEY is not set (env var or config)")
    return key


@dataclass
class DeepLClient:
    """Thin DeepL /v2/translate client built on reqretry for retry/backoff."""

    api_key: str
    retry_config: reqretry.RetryConfig = field(
        default_factory=lambda: reqretry.RetryConfig(retry_status_codes=_RETRY_STATUS_CODES)
    )

    def __post_init__(self) -> None:
        if not self.api_key:
            raise DeepLConfigError("DeepL API key is empty")
        self._session = reqretry.Session(self.retry_config)

    @property
    def base_url(self) -> str:
        # Free-tier keys are suffixed ":fx" and only work against the free host.
        return DEEPL_FREE_URL if self.api_key.endswith(":fx") else DEEPL_PRO_URL

    def translate(self, texts: list[str], *, source_lang: str, target_lang: str) -> list[str]:
        """Translate `texts` (in order) from `source_lang` to `target_lang`.

        `texts` may be multi-line (each entry stays one translation unit, so a
        grouped comment block is translated with its full context). Returns an
        empty list for empty input without calling the API.
        """
        if not texts:
            return []

        source = _resolve_lang(_SOURCE_LANG, source_lang, "source")
        target = _resolve_lang(_TARGET_LANG, target_lang, "target")

        try:
            resp = self._session.post(
                self.base_url,
                headers={"Authorization": f"DeepL-Auth-Key {self.api_key}"},
                data={"text": texts, "source_lang": source, "target_lang": target},
            )
        except requests.exceptions.RequestException as exc:
            raise DeepLError(f"DeepL request failed: {exc}") from exc

        if resp.status_code != 200:
            raise DeepLError(f"DeepL API returned {resp.status_code}: {resp.text[:300]}")

        payload = resp.json()
        return [t["text"] for t in payload["translations"]]

    def translate_to_many(
        self, texts: list[str], *, source_lang: str, target_langs: list[str]
    ) -> dict[str, list[str]]:
        """Translate `texts` into each of `target_langs` (one API call per target,
        since DeepL's target_lang is singular per request)."""
        return {
            target: self.translate(texts, source_lang=source_lang, target_lang=target)
            for target in target_langs
        }

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "DeepLClient":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()


def _resolve_lang(table: dict[str, str], code: str, role: str) -> str:
    try:
        return table[code.lower()]
    except KeyError:
        raise DeepLConfigError(
            f"Unsupported {role} language code: {code!r} (supported: {sorted(SUPPORTED_LANGUAGES)})"
        ) from None
