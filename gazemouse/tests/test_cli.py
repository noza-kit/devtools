from pathlib import Path

from typer.testing import CliRunner

from gazemouse.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "calibrate" in result.output
    assert "start" in result.output


def test_calibrate_help():
    result = runner.invoke(app, ["calibrate", "--help"])
    assert result.exit_code == 0


def test_start_help():
    result = runner.invoke(app, ["start", "--help"])
    assert result.exit_code == 0


def test_start_missing_calibration_fails(tmp_path: Path):
    result = runner.invoke(app, ["start", "--calibration", str(tmp_path / "missing.json")])
    assert result.exit_code == 1
    assert "エラー" in result.output


def test_start_missing_face_model_fails(tmp_path: Path):
    from gazemouse.calibration import CalibrationData
    from gazemouse.config import save_calibration

    calibration_path = tmp_path / "calibration.json"
    save_calibration(
        CalibrationData(iris_min_x=0.3, iris_max_x=0.7, iris_min_y=0.3, iris_max_y=0.7, screen_width=1920, screen_height=1080),
        calibration_path,
    )

    result = runner.invoke(
        app, ["start", "--calibration", str(calibration_path), "--face-model", str(tmp_path / "missing.task")]
    )
    assert result.exit_code == 1
    assert "エラー" in result.output


def test_calibrate_missing_face_model_fails(tmp_path: Path):
    result = runner.invoke(app, ["calibrate", "--face-model", str(tmp_path / "missing.task")])
    assert result.exit_code == 1
    assert "エラー" in result.output
