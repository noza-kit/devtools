from __future__ import annotations

from pathlib import Path

import pytest

from airshare.config import Settings


@pytest.fixture
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    send_dir = tmp_path / "send"
    receive_dir = tmp_path / "received"
    send_dir.mkdir()
    receive_dir.mkdir()
    monkeypatch.setattr(Settings, "runtime_dir", property(lambda self: tmp_path / ".airshare"))
    return Settings(host="127.0.0.1", port=8000, send_dir=send_dir, receive_dir=receive_dir, passcode=None)
