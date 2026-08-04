import pytest

from confload import ConfigError, load_config


def test_reference_other_config_key(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("base_dir: /data\ndataset_path: ${base_dir}/train\n", encoding="utf-8")

    config = load_config(path)

    assert config.dataset_path == "/data/train"


def test_reference_nested_config_key_via_dotted_path(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "model:\n  name: resnet50\ndisplay_name: 'Model: ${model.name}'\n",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.display_name == "Model: resnet50"


def test_reference_env_var(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("api_key: ${API_KEY}\n", encoding="utf-8")
    monkeypatch.setenv("API_KEY", "secret123")

    config = load_config(path)

    assert config.api_key == "secret123"


def test_config_key_takes_precedence_over_env_var(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("name: from_config\ngreeting: 'hi ${name}'\n", encoding="utf-8")
    monkeypatch.setenv("name", "from_env")

    config = load_config(path)

    assert config.greeting == "hi from_config"


def test_default_value_used_when_unresolved(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("api_key: ${API_KEY:-changeme}\n", encoding="utf-8")

    config = load_config(path)

    assert config.api_key == "changeme"


def test_reference_resolved_after_env_override(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("base_dir: /data\ndataset_path: ${base_dir}/train\n", encoding="utf-8")
    monkeypatch.setenv("APP_BASE_DIR", "/mnt/data")

    config = load_config(path)

    assert config.dataset_path == "/mnt/data/train"


def test_unresolved_reference_raises_clear_error(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("dataset_path: ${GHOST_VAR}/train\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="GHOST_VAR"):
        load_config(path)


def test_circular_reference_raises(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("a: ${b}\nb: ${a}\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Circular"):
        load_config(path)
