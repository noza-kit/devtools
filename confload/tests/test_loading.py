from confload import load_config


def test_load_yaml_basic(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("learning_rate: 0.01\nbatch_size: 32\n", encoding="utf-8")

    config = load_config(path)

    assert config.learning_rate == 0.01
    assert config["learning_rate"] == 0.01
    assert config.batch_size == 32


def test_load_json_basic(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"learning_rate": 0.01, "batch_size": 32}', encoding="utf-8")

    config = load_config(path)

    assert config.learning_rate == 0.01
    assert config["batch_size"] == 32


def test_nested_attribute_and_item_access(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("model:\n  name: resnet50\n  layers: 50\n", encoding="utf-8")

    config = load_config(path)

    assert config.model.name == "resnet50"
    assert config["model"]["layers"] == 50


def test_list_of_mappings_is_wrapped(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "steps:\n  - op: grayscale\n  - op: resize\n    width: 10\n",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.steps[0].op == "grayscale"
    assert config.steps[1].width == 10


def test_to_dict_roundtrip(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "model:\n  name: resnet50\nsteps:\n  - op: grayscale\n",
        encoding="utf-8",
    )

    config = load_config(path)

    assert config.to_dict() == {
        "model": {"name": "resnet50"},
        "steps": [{"op": "grayscale"}],
    }


def test_get_with_default(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("learning_rate: 0.01\n", encoding="utf-8")

    config = load_config(path)

    assert config.get("learning_rate") == 0.01
    assert config.get("missing_key", "fallback") == "fallback"


def test_missing_attribute_raises_attribute_error(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("learning_rate: 0.01\n", encoding="utf-8")

    config = load_config(path)

    try:
        config.ghost
        assert False, "expected AttributeError"
    except AttributeError as exc:
        assert "ghost" in str(exc)
