from __future__ import annotations

import os

from airshare.config import Settings
from airshare.runtime import clear_runtime_info, generate_token, read_runtime_info, write_runtime_info


def test_write_then_read_round_trips(settings: Settings) -> None:
    token = generate_token()
    write_runtime_info(settings, token)

    info = read_runtime_info(settings)
    assert info is not None
    assert info.pid == os.getpid()
    assert info.port == settings.port
    assert info.token == token


def test_read_returns_none_when_missing(settings: Settings) -> None:
    assert read_runtime_info(settings) is None


def test_clear_removes_file(settings: Settings) -> None:
    write_runtime_info(settings, generate_token())
    clear_runtime_info(settings)
    assert read_runtime_info(settings) is None


def test_clear_is_safe_when_already_missing(settings: Settings) -> None:
    clear_runtime_info(settings)  # should not raise


def test_generate_token_is_unique() -> None:
    assert generate_token() != generate_token()
