from __future__ import annotations

from pathlib import Path

import pytest

from airshare.config import Settings
from airshare.shortcut import SHORTCUT_NAME, create_desktop_shortcut


def test_create_desktop_shortcut_writes_bat_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    settings = Settings(
        host="0.0.0.0", port=8123, send_dir=tmp_path / "send", receive_dir=tmp_path / "received", passcode="1234"
    )

    path = create_desktop_shortcut(settings)

    assert path == tmp_path / "Desktop" / SHORTCUT_NAME
    content = path.read_text(encoding="utf-8")
    assert "set AIRSHARE_PORT=8123" in content
    assert "set AIRSHARE_PASSCODE=1234" in content
    assert "start" in content


def test_create_desktop_shortcut_omits_passcode_when_unset(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    settings = Settings(
        host="0.0.0.0", port=8000, send_dir=tmp_path / "send", receive_dir=tmp_path / "received", passcode=None
    )

    path = create_desktop_shortcut(settings)
    content = path.read_text(encoding="utf-8")
    assert "AIRSHARE_PASSCODE" not in content
