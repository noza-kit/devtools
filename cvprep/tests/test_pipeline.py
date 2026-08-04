import pytest

from cvprep.pipeline import Pipeline, UnknownOpError
from cvprep.presets import PresetNotFoundError


def test_from_steps_runs_ops_in_order(sample_image):
    pipeline = Pipeline.from_steps(
        [
            {"op": "grayscale"},
            {"op": "blur", "ksize": 3},
            {"op": "canny", "threshold1": 50, "threshold2": 150},
        ]
    )
    out = pipeline.run(sample_image)
    assert out.ndim == 2
    assert out.dtype.name == "uint8"


def test_from_steps_missing_op_key_raises():
    with pytest.raises(ValueError):
        Pipeline.from_steps([{"width": 10}])


def test_unknown_op_raises(sample_image):
    pipeline = Pipeline.from_steps([{"op": "not_a_real_op"}])
    with pytest.raises(UnknownOpError):
        pipeline.run(sample_image)


def test_from_preset_loads_and_runs(cvprep_home, sample_image):
    (cvprep_home).mkdir(parents=True, exist_ok=True)
    (cvprep_home / "presets.yaml").write_text(
        "presets:\n  gray:\n    - op: grayscale\n", encoding="utf-8"
    )
    pipeline = Pipeline.from_preset("gray")
    out = pipeline.run(sample_image)
    assert out.ndim == 2


def test_from_preset_missing_raises(cvprep_home):
    with pytest.raises(PresetNotFoundError):
        Pipeline.from_preset("ghost")
