from pathlib import Path

import pytest

from snapclip.config import Settings, load_settings, save_settings, with_overrides


def test_default_settings_when_no_config_file():
    settings = load_settings(config_path=None)
    # a real default path may or may not exist on the test machine; just check it doesn't crash
    # and produces a valid Settings when nothing custom is configured elsewhere.
    assert settings.mode in ("markdown", "latex")


def test_load_settings_explicit_missing_path_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_settings(config_path=tmp_path / "missing.yaml")


def test_load_settings_from_file(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("mode: latex\nimg_dir: ./tex_figures\n", encoding="utf-8")
    settings = load_settings(config_path=cfg)
    assert settings.mode == "latex"
    assert settings.img_dir == Path("./tex_figures").expanduser()


def test_load_settings_partial_file_keeps_other_default(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("mode: latex\n", encoding="utf-8")
    settings = load_settings(config_path=cfg)
    assert settings.mode == "latex"
    assert settings.img_dir == Path("./images").expanduser()


def test_settings_rejects_invalid_mode():
    with pytest.raises(ValueError):
        Settings(mode="html")


def test_save_and_reload_round_trip(tmp_path: Path):
    cfg_path = tmp_path / "config.yaml"
    save_settings(Settings(mode="latex", img_dir=tmp_path / "figs"), cfg_path)
    reloaded = load_settings(config_path=cfg_path)
    assert reloaded.mode == "latex"
    assert reloaded.img_dir == tmp_path / "figs"


def test_with_overrides_only_changes_given_fields(tmp_path: Path):
    base = Settings(mode="markdown", img_dir=tmp_path / "images")
    updated = with_overrides(base, mode="latex")
    assert updated.mode == "latex"
    assert updated.img_dir == base.img_dir


def test_with_overrides_no_args_returns_equivalent_settings(tmp_path: Path):
    base = Settings(mode="markdown", img_dir=tmp_path / "images")
    assert with_overrides(base) == base
