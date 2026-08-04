from __future__ import annotations

from pathlib import Path

import pytest

from airshare.config import DEFAULT_PORT, load_settings


def test_load_settings_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("AIRSHARE_PORT", raising=False)
    monkeypatch.delenv("AIRSHARE_PASSCODE", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    settings = load_settings()

    assert settings.port == DEFAULT_PORT
    assert settings.passcode is None
    assert settings.send_dir == (tmp_path / "Documents" / "AirShare" / "send").resolve()
    assert settings.receive_dir == (tmp_path / "Documents" / "AirShare" / "received").resolve()
    assert settings.send_dir.is_dir()
    assert settings.receive_dir.is_dir()


def test_load_settings_cli_overrides_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AIRSHARE_PORT", "9999")
    monkeypatch.setenv("AIRSHARE_PASSCODE", "envcode")

    settings = load_settings(port=8123, passcode="clicode", send_dir=tmp_path / "s", receive_dir=tmp_path / "r")

    assert settings.port == 8123
    assert settings.passcode == "clicode"


def test_load_settings_env_overrides_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AIRSHARE_PORT", "9999")
    monkeypatch.setenv("AIRSHARE_PASSCODE", "envcode")

    settings = load_settings(send_dir=tmp_path / "s", receive_dir=tmp_path / "r")

    assert settings.port == 9999
    assert settings.passcode == "envcode"
