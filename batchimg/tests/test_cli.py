import cv2
from typer.testing import CliRunner

from batchimg.cli import app

runner = CliRunner()


def test_not_a_directory_fails(tmp_path):
    result = runner.invoke(app, [str(tmp_path / "missing")])
    assert result.exit_code == 1
    assert "Not a directory" in result.output


def test_no_matching_files_reports_and_exits_cleanly(tmp_path):
    result = runner.invoke(app, [str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "No matching images or videos found" in result.output


def test_dry_run_shows_preview_and_writes_nothing(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")

    result = runner.invoke(app, [str(tmp_path), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "a.jpg" in result.output
    assert "dry run" in result.output
    assert not (tmp_path / "batchimg_out").exists()


def test_confirmation_declined_aborts(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")

    result = runner.invoke(app, [str(tmp_path)], input="n\n")

    assert result.exit_code == 1
    assert "Aborted" in result.output
    assert not (tmp_path / "batchimg_out").exists()


def test_confirmation_accepted_processes_files(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")

    result = runner.invoke(app, [str(tmp_path)], input="y\n")

    assert result.exit_code == 0, result.output
    assert (tmp_path / "batchimg_out" / "a.jpg").exists()
    assert (tmp_path / "a.jpg").exists()  # original untouched


def test_yes_flag_skips_prompt(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")

    result = runner.invoke(app, [str(tmp_path), "--yes"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "batchimg_out" / "a.jpg").exists()


def test_resize_and_rename_produce_expected_output(tmp_path, make_image):
    make_image(tmp_path / "a.jpg", size=(40, 30))

    result = runner.invoke(
        app, [str(tmp_path), "--resize", "20x20", "--no-keep-aspect", "--rename", "img_{n}", "--yes"]
    )

    assert result.exit_code == 0, result.output
    out_path = tmp_path / "batchimg_out" / "img_0001.jpg"
    assert out_path.exists()
    image = cv2.imread(str(out_path))
    assert image.shape[:2] == (20, 20)


def test_invalid_resize_format_fails(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")

    result = runner.invoke(app, [str(tmp_path), "--resize", "bogus", "--yes"])

    assert result.exit_code == 1
    assert "Invalid size" in result.output


def test_trim_end_before_trim_start_fails(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")

    result = runner.invoke(app, [str(tmp_path), "--trim-start", "5", "--trim-end", "1", "--yes"])

    assert result.exit_code == 1
    assert "--trim-end" in result.output


def test_in_place_with_output_dir_fails(tmp_path, make_image):
    make_image(tmp_path / "a.jpg")

    result = runner.invoke(app, [str(tmp_path), "--in-place", "--output-dir", str(tmp_path / "out"), "--yes"])

    assert result.exit_code == 1
    assert "--in-place" in result.output


def test_in_place_overwrites_original(tmp_path, make_image):
    make_image(tmp_path / "a.jpg", size=(40, 30))

    result = runner.invoke(app, [str(tmp_path), "--in-place", "--resize", "20x20", "--no-keep-aspect", "--yes"])

    assert result.exit_code == 0, result.output
    image = cv2.imread(str(tmp_path / "a.jpg"))
    assert image.shape[:2] == (20, 20)
    assert not (tmp_path / "batchimg_out").exists()


def test_recursive_preserves_subdirectory_structure(tmp_path, make_image):
    make_image(tmp_path / "sub" / "a.jpg")

    result = runner.invoke(app, [str(tmp_path), "--recursive", "--yes"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "batchimg_out" / "sub" / "a.jpg").exists()


def test_non_recursive_ignores_subdirectory(tmp_path, make_image):
    make_image(tmp_path / "sub" / "a.jpg")

    result = runner.invoke(app, [str(tmp_path), "--yes"])

    assert result.exit_code == 0, result.output
    assert "No matching images or videos found" in result.output


def test_video_is_processed(tmp_path, make_video):
    make_video(tmp_path / "clip.mp4", frames=10, size=(64, 48), fps=10.0)

    result = runner.invoke(app, [str(tmp_path), "--resize", "32x32", "--no-keep-aspect", "--yes"])

    assert result.exit_code == 0, result.output
    out_path = tmp_path / "batchimg_out" / "clip.mp4"
    assert out_path.exists()
    cap = cv2.VideoCapture(str(out_path))
    ok, frame = cap.read()
    cap.release()
    assert ok
    assert frame.shape[:2] == (32, 32)
