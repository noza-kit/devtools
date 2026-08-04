import cv2
from typer.testing import CliRunner

from cvprep.cli import app
from cvprep.presets import presets_path

runner = CliRunner()


def _write_presets(cvprep_home):
    cvprep_home.mkdir(parents=True, exist_ok=True)
    (cvprep_home / "presets.yaml").write_text(
        "presets:\n  gray:\n    - op: grayscale\n",
        encoding="utf-8",
    )


def _write_image(path, image):
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)


def test_init_creates_presets_file(cvprep_home):
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output
    assert presets_path().exists()


def test_init_without_force_reports_existing(cvprep_home):
    runner.invoke(app, ["init"])
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0, result.output
    assert "already exists" in result.output


def test_list_reports_no_presets_when_empty(cvprep_home):
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0, result.output
    assert "No presets found" in result.output


def test_list_shows_preset_names(cvprep_home):
    _write_presets(cvprep_home)
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0, result.output
    assert "gray" in result.output


def test_show_prints_preset_steps(cvprep_home):
    _write_presets(cvprep_home)
    result = runner.invoke(app, ["show", "gray"])
    assert result.exit_code == 0, result.output
    assert "grayscale" in result.output


def test_show_unknown_preset_fails(cvprep_home):
    result = runner.invoke(app, ["show", "ghost"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_run_applies_preset_and_writes_output(cvprep_home, tmp_path, sample_image):
    _write_presets(cvprep_home)
    input_path = tmp_path / "input.png"
    _write_image(input_path, sample_image)

    result = runner.invoke(app, ["run", "gray", str(input_path)])
    assert result.exit_code == 0, result.output

    out_path = tmp_path / "input.cvprep.png"
    assert out_path.exists()


def test_run_with_explicit_output(cvprep_home, tmp_path, sample_image):
    _write_presets(cvprep_home)
    input_path = tmp_path / "input.png"
    _write_image(input_path, sample_image)
    out_path = tmp_path / "custom.png"

    result = runner.invoke(app, ["run", "gray", str(input_path), "--output", str(out_path)])
    assert result.exit_code == 0, result.output
    assert out_path.exists()


def test_run_unknown_preset_fails(cvprep_home, tmp_path, sample_image):
    input_path = tmp_path / "input.png"
    _write_image(input_path, sample_image)

    result = runner.invoke(app, ["run", "ghost", str(input_path)])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_batch_processes_all_matching_images(cvprep_home, tmp_path, sample_image):
    _write_presets(cvprep_home)
    input_dir = tmp_path / "images"
    input_dir.mkdir()
    _write_image(input_dir / "a.png", sample_image)
    _write_image(input_dir / "b.png", sample_image)
    (input_dir / "notes.txt").write_text("not an image", encoding="utf-8")

    result = runner.invoke(app, ["batch", "gray", str(input_dir)])
    assert result.exit_code == 0, result.output
    assert "Processed 2/2" in result.output

    out_dir = input_dir / "cvprep_out"
    assert (out_dir / "a.png").exists()
    assert (out_dir / "b.png").exists()


def test_batch_no_matches_reports_and_exits_cleanly(cvprep_home, tmp_path):
    input_dir = tmp_path / "empty"
    input_dir.mkdir()

    result = runner.invoke(app, ["batch", "gray", str(input_dir)])
    assert result.exit_code == 0, result.output
    assert "No matching images found" in result.output


def test_batch_not_a_directory_fails(cvprep_home, tmp_path, sample_image):
    input_path = tmp_path / "input.png"
    _write_image(input_path, sample_image)

    result = runner.invoke(app, ["batch", "gray", str(input_path)])
    assert result.exit_code == 1
    assert "Not a directory" in result.output
