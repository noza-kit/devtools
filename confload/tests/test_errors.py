import pytest

from confload import ConfigError, load_config


def test_file_not_found_raises_clear_error(tmp_path):
    path = tmp_path / "missing.yaml"

    with pytest.raises(ConfigError, match="not found"):
        load_config(path)


def test_unsupported_extension_raises(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("learning_rate = 0.01\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Unsupported"):
        load_config(path)


def test_invalid_yaml_syntax_raises(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("learning_rate: [0.01\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Invalid YAML"):
        load_config(path)


def test_invalid_json_syntax_raises(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"learning_rate": 0.01,}', encoding="utf-8")

    with pytest.raises(ConfigError, match="Invalid JSON"):
        load_config(path)


def test_top_level_non_mapping_raises(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("- one\n- two\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="top-level mapping"):
        load_config(path)


def test_empty_yaml_file_is_empty_mapping(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("", encoding="utf-8")

    config = load_config(path)

    assert config.to_dict() == {}
