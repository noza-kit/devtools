import pytest

from confload import ConfigError, load_config


def test_all_required_keys_present_loads_fine(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("learning_rate: 0.01\nmodel:\n  name: resnet50\n", encoding="utf-8")

    config = load_config(path, required=["learning_rate", "model.name"])

    assert config.learning_rate == 0.01


def test_missing_top_level_key_raises_with_key_name(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("model:\n  name: resnet50\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="learning_rate"):
        load_config(path, required=["learning_rate"])


def test_missing_nested_key_raises_with_dotted_path(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("model:\n  layers: 50\n", encoding="utf-8")

    with pytest.raises(ConfigError, match=r"model\.name"):
        load_config(path, required=["model.name"])


def test_multiple_missing_keys_listed_together(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("batch_size: 32\n", encoding="utf-8")

    with pytest.raises(ConfigError) as exc_info:
        load_config(path, required=["learning_rate", "model.name"])

    message = str(exc_info.value)
    assert "learning_rate" in message
    assert "model.name" in message


def test_required_key_satisfied_by_env_override(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("batch_size: 32\n", encoding="utf-8")
    monkeypatch.setenv("APP_LEARNING_RATE", "0.02")

    config = load_config(path, required=["learning_rate"])

    assert config.learning_rate == 0.02
