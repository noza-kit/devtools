from pathlib import Path

import pytest

from airshare.watch_config import WatchSettings, load_watch_settings


def test_missing_config_uses_default_inbox_dir(tmp_path: Path):
    default_inbox = tmp_path / "received"
    settings = load_watch_settings(None, default_inbox_dir=default_inbox)
    assert settings.inbox_dir == default_inbox
    assert settings.routing == ()
    assert settings.hooks == {}
    assert settings.cleanup.enabled is True


def test_explicit_missing_path_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_watch_settings(tmp_path / "missing.yaml", default_inbox_dir=tmp_path)


def test_load_full_config(tmp_path: Path):
    # YAML double-quoted strings treat backslashes as escapes, which
    # corrupts a raw Windows path -- .as_posix() (forward slashes) sidesteps
    # that; Path() on the read-back value still resolves it correctly.
    cfg = tmp_path / "watch.yaml"
    cfg.write_text(
        f"""
inbox_dir: "{(tmp_path / 'inbox').as_posix()}"
debounce_seconds: 5
routing:
  pictures:
    extensions: [".jpg", ".png"]
    destination: "{(tmp_path / 'Pictures').as_posix()}"
  docs:
    extensions: [".pdf"]
    destination: "{(tmp_path / 'Documents').as_posix()}"
hooks:
  ".pdf": "pdfcraft compress {{filepath}} --replace"
cleanup:
  enabled: true
  expire_days: 14
""",
        encoding="utf-8",
    )
    settings = load_watch_settings(cfg, default_inbox_dir=tmp_path)
    assert settings.inbox_dir == tmp_path / "inbox"
    assert settings.debounce_seconds == 5
    assert len(settings.routing) == 2
    assert settings.routing[0].name == "pictures"
    assert settings.routing[0].extensions == (".jpg", ".png")
    assert settings.hooks[".pdf"] == "pdfcraft compress {filepath} --replace"
    assert settings.cleanup.expire_days == 14


def test_config_without_inbox_dir_falls_back_to_default(tmp_path: Path):
    cfg = tmp_path / "watch.yaml"
    cfg.write_text("debounce_seconds: 1\n", encoding="utf-8")
    default_inbox = tmp_path / "airshare_received"
    settings = load_watch_settings(cfg, default_inbox_dir=default_inbox)
    assert settings.inbox_dir == default_inbox


def test_cleanup_disabled(tmp_path: Path):
    cfg = tmp_path / "watch.yaml"
    cfg.write_text("cleanup:\n  enabled: false\n", encoding="utf-8")
    settings = load_watch_settings(cfg, default_inbox_dir=tmp_path)
    assert settings.cleanup.enabled is False


def test_default_settings_object_directly():
    settings = WatchSettings(inbox_dir=Path("/tmp/inbox"))
    assert settings.debounce_seconds == 3.0
    assert settings.cleanup.expire_days == 7
