from __future__ import annotations

import pytest

from claude_bridge.config import ConfigError, load_secrets, load_settings


def _write_config(tmp_path, text):
    path = tmp_path / "bridge.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_settings_happy_path(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    config_path = _write_config(
        tmp_path,
        f"""
projects:
  - alias: hobby
    path: "{proj.as_posix()}"
default_project: hobby
default_mode: summary
timeout_seconds: 600
""",
    )
    settings = load_settings(config_path)
    assert settings.projects[0].alias == "hobby"
    assert settings.default_project == "hobby"
    assert settings.default_mode == "summary"
    assert settings.timeout_seconds == 600
    assert settings.progress_interval_seconds == 20  # default


def test_missing_config_file_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_settings(tmp_path / "nonexistent.yaml")


def test_no_projects_raises(tmp_path):
    config_path = _write_config(tmp_path, "projects: []\n")
    with pytest.raises(ConfigError):
        load_settings(config_path)


def test_duplicate_alias_raises(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    config_path = _write_config(
        tmp_path,
        f"""
projects:
  - alias: hobby
    path: "{proj.as_posix()}"
  - alias: hobby
    path: "{proj.as_posix()}"
""",
    )
    with pytest.raises(ConfigError):
        load_settings(config_path)


def test_nonexistent_project_path_raises(tmp_path):
    config_path = _write_config(
        tmp_path,
        """
projects:
  - alias: hobby
    path: "C:/definitely/does/not/exist/xyz"
""",
    )
    with pytest.raises(ConfigError):
        load_settings(config_path)


def test_invalid_default_mode_raises(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    config_path = _write_config(
        tmp_path,
        f"""
projects:
  - alias: hobby
    path: "{proj.as_posix()}"
default_mode: bogus
""",
    )
    with pytest.raises(ConfigError):
        load_settings(config_path)


def test_unknown_default_project_raises(tmp_path):
    proj = tmp_path / "proj"
    proj.mkdir()
    config_path = _write_config(
        tmp_path,
        f"""
projects:
  - alias: hobby
    path: "{proj.as_posix()}"
default_project: nonexistent
""",
    )
    with pytest.raises(ConfigError):
        load_settings(config_path)


# -- load_secrets --------------------------------------------------------------


def test_load_secrets_happy_path():
    env = {
        "CLAUDE_BRIDGE_BOT_TOKEN": "tok",
        "CLAUDE_BRIDGE_CHANNEL_ID": "123",
        "CLAUDE_BRIDGE_ALLOWED_USER_IDS": "1,2, 3",
    }
    secrets = load_secrets(env)
    assert secrets.bot_token == "tok"
    assert secrets.channel_id == "123"
    assert secrets.allowed_user_ids == frozenset({"1", "2", "3"})


def test_load_secrets_missing_var_raises():
    with pytest.raises(ConfigError):
        load_secrets({"CLAUDE_BRIDGE_BOT_TOKEN": "tok"})


def test_load_secrets_empty_allowed_ids_raises():
    env = {
        "CLAUDE_BRIDGE_BOT_TOKEN": "tok",
        "CLAUDE_BRIDGE_CHANNEL_ID": "123",
        "CLAUDE_BRIDGE_ALLOWED_USER_IDS": "  ,  ",
    }
    with pytest.raises(ConfigError):
        load_secrets(env)
