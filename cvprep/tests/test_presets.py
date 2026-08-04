import pytest

from cvprep.presets import (
    PresetNotFoundError,
    get_preset,
    init_presets_file,
    list_preset_names,
    load_presets,
    presets_path,
)


def test_load_presets_empty_when_file_missing(cvprep_home):
    assert load_presets() == {}


def test_load_presets_reads_yaml(cvprep_home):
    cvprep_home.mkdir(parents=True, exist_ok=True)
    (cvprep_home / "presets.yaml").write_text(
        "presets:\n  a:\n    - op: grayscale\n  b:\n    - op: resize\n      width: 10\n",
        encoding="utf-8",
    )
    presets = load_presets()
    assert set(presets) == {"a", "b"}
    assert presets["b"] == [{"op": "resize", "width": 10}]


def test_get_preset_missing_raises(cvprep_home):
    with pytest.raises(PresetNotFoundError):
        get_preset("ghost")


def test_list_preset_names_sorted(cvprep_home):
    cvprep_home.mkdir(parents=True, exist_ok=True)
    (cvprep_home / "presets.yaml").write_text(
        "presets:\n  zeta:\n    - op: grayscale\n  alpha:\n    - op: grayscale\n",
        encoding="utf-8",
    )
    assert list_preset_names() == ["alpha", "zeta"]


def test_init_presets_file_creates_starter_file(cvprep_home):
    created = init_presets_file()
    assert created is True
    assert presets_path().exists()
    assert "edge_prep" in list_preset_names()


def test_init_presets_file_does_not_overwrite_without_force(cvprep_home):
    init_presets_file()
    (presets_path()).write_text("presets:\n  custom:\n    - op: grayscale\n", encoding="utf-8")

    created = init_presets_file()
    assert created is False
    assert list_preset_names() == ["custom"]


def test_init_presets_file_force_overwrites(cvprep_home):
    init_presets_file()
    (presets_path()).write_text("presets:\n  custom:\n    - op: grayscale\n", encoding="utf-8")

    created = init_presets_file(force=True)
    assert created is True
    assert "custom" not in list_preset_names()
