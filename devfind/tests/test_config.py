from __future__ import annotations

from pathlib import Path

import pytest

from devfind.config import DEFAULT_EXCLUDE, DEFAULT_TARGET_DIRS, load_settings


def test_defaults_used_when_no_config_path_and_default_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("devfind.config.DEFAULT_CONFIG_PATH", tmp_path / "does-not-exist.yaml")

    settings = load_settings()

    assert settings.target_dirs == [Path(d).expanduser() for d in DEFAULT_TARGET_DIRS]
    assert settings.exclude == DEFAULT_EXCLUDE


def test_default_config_path_used_when_present(monkeypatch, tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "target_dirs:\n  - ~/Pictures\nexclude:\n  - build\n",
        encoding="utf-8",
    )
    monkeypatch.setattr("devfind.config.DEFAULT_CONFIG_PATH", config_file)

    settings = load_settings()

    assert settings.target_dirs == [Path("~/Pictures").expanduser()]
    assert settings.exclude == ["build"]


def test_explicit_config_path_overrides_target_dirs_and_exclude(tmp_path):
    config_file = tmp_path / "custom.yaml"
    config_file.write_text(
        "target_dirs:\n  - ~/Projects\n  - ~/Notes\nexclude:\n  - dist\n  - .cache\n",
        encoding="utf-8",
    )

    settings = load_settings(config_file)

    assert settings.target_dirs == [Path("~/Projects").expanduser(), Path("~/Notes").expanduser()]
    assert settings.exclude == ["dist", ".cache"]


def test_partial_config_falls_back_to_default_exclude(tmp_path):
    config_file = tmp_path / "partial.yaml"
    config_file.write_text("target_dirs:\n  - ~/Projects\n", encoding="utf-8")

    settings = load_settings(config_file)

    assert settings.target_dirs == [Path("~/Projects").expanduser()]
    assert settings.exclude == DEFAULT_EXCLUDE


def test_explicit_missing_config_path_raises(tmp_path):
    missing = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError):
        load_settings(missing)
