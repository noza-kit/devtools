from pathlib import Path

import pytest

from gazemouse.calibration import CalibrationData
from gazemouse.config import load_calibration, save_calibration


def test_save_and_load_round_trip(tmp_path: Path):
    path = tmp_path / "calibration.json"
    data = CalibrationData(iris_min_x=0.3, iris_max_x=0.7, iris_min_y=0.25, iris_max_y=0.75, screen_width=1920, screen_height=1080)
    saved_path = save_calibration(data, path)
    assert saved_path == path

    loaded = load_calibration(path)
    assert loaded == data


def test_load_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_calibration(tmp_path / "missing.json")


def test_save_creates_parent_directory(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "calibration.json"
    data = CalibrationData(iris_min_x=0.3, iris_max_x=0.7, iris_min_y=0.25, iris_max_y=0.75, screen_width=1920, screen_height=1080)
    save_calibration(data, path)
    assert path.exists()
