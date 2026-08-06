from pathlib import Path

import pytest

from notesearch.config import Settings, load_settings


def test_default_settings():
    settings = Settings()
    assert settings.chunk_size == 500
    assert settings.chunk_overlap == 50
    assert settings.exclude == ["venv", ".venv", "node_modules", "__pycache__", ".git"]


def test_load_settings_explicit_missing_path_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_settings(config_path=tmp_path / "missing.yaml")


def test_load_settings_from_file(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "target_dirs:\n  - ~/notes\nexclude:\n  - build\nchunk_size: 300\nauto_convert_pdf: true\n",
        encoding="utf-8",
    )
    settings = load_settings(config_path=cfg)
    assert settings.target_dirs == [Path("~/notes").expanduser()]
    assert settings.exclude == ["build"]
    assert settings.chunk_size == 300
    assert settings.auto_convert_pdf is True


def test_load_settings_partial_file_keeps_other_defaults(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("chunk_size: 999\n", encoding="utf-8")
    settings = load_settings(config_path=cfg)
    assert settings.chunk_size == 999
    assert settings.chunk_overlap == 50  # untouched default


def test_load_settings_gemini_api_key(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("gemini_api_key: test-key-123\n", encoding="utf-8")
    settings = load_settings(config_path=cfg)
    assert settings.gemini_api_key == "test-key-123"


def test_settings_default_gemini_api_key_is_none():
    assert Settings().gemini_api_key is None
