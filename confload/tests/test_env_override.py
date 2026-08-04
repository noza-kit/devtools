from confload import load_config


def test_env_override_top_level(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("learning_rate: 0.01\n", encoding="utf-8")
    monkeypatch.setenv("APP_LEARNING_RATE", "0.02")

    config = load_config(path)

    assert config.learning_rate == 0.02
    assert isinstance(config.learning_rate, float)


def test_env_override_type_coercion(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("debug: false\nworkers: 1\n", encoding="utf-8")
    monkeypatch.setenv("APP_DEBUG", "true")
    monkeypatch.setenv("APP_WORKERS", "4")

    config = load_config(path)

    assert config.debug is True
    assert config.workers == 4


def test_env_override_falls_back_to_string_on_unparsable_value(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("name: default\n", encoding="utf-8")
    monkeypatch.setenv("APP_NAME", "resnet-50: extra")

    config = load_config(path)

    assert config.name == "resnet-50: extra"


def test_env_override_nested_via_double_underscore(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("model:\n  name: resnet50\n", encoding="utf-8")
    monkeypatch.setenv("APP_MODEL__NAME", "resnet101")

    config = load_config(path)

    assert config.model.name == "resnet101"


def test_env_override_creates_new_nested_key(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("model:\n  name: resnet50\n", encoding="utf-8")
    monkeypatch.setenv("APP_MODEL__LAYERS", "101")

    config = load_config(path)

    assert config.model.layers == 101


def test_custom_env_prefix(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("learning_rate: 0.01\n", encoding="utf-8")
    monkeypatch.setenv("MYAPP_LEARNING_RATE", "0.05")
    monkeypatch.setenv("APP_LEARNING_RATE", "0.02")

    config = load_config(path, env_prefix="MYAPP")

    assert config.learning_rate == 0.05


def test_unrelated_env_vars_are_ignored(tmp_path, monkeypatch):
    path = tmp_path / "config.yaml"
    path.write_text("learning_rate: 0.01\n", encoding="utf-8")
    monkeypatch.setenv("PATH_EXTRA", "should-not-apply")
    monkeypatch.setenv("APPX_LEARNING_RATE", "0.09")

    config = load_config(path)

    assert config.learning_rate == 0.01
