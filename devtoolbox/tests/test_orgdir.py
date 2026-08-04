from typer.testing import CliRunner

from devtoolbox.common.paths import orgdir_log_path
from devtoolbox.orgdir.cli import app

runner = CliRunner()


def _make_target(tmp_path):
    target = tmp_path / "messy"
    target.mkdir()
    (target / "photo.jpg").write_text("img", encoding="utf-8")
    (target / "report.pdf").write_text("doc", encoding="utf-8")
    (target / "notes.xyz").write_text("unknown ext", encoding="utf-8")
    (target / "README").write_text("no ext", encoding="utf-8")
    return target


def test_organizes_files_into_category_folders(tmp_path):
    target = _make_target(tmp_path)

    result = runner.invoke(app, [str(target)])
    assert result.exit_code == 0, result.output

    assert (target / "images" / "photo.jpg").read_text(encoding="utf-8") == "img"
    assert (target / "documents" / "report.pdf").read_text(encoding="utf-8") == "doc"
    assert (target / "others" / "notes.xyz").read_text(encoding="utf-8") == "unknown ext"
    assert (target / "others" / "README").read_text(encoding="utf-8") == "no ext"
    assert not (target / "photo.jpg").exists()


def test_dry_run_reports_plan_without_moving_files(tmp_path):
    target = _make_target(tmp_path)

    result = runner.invoke(app, [str(target), "--dry-run"])
    assert result.exit_code == 0, result.output

    assert "would move" in result.output
    assert "photo.jpg -> images/photo.jpg" in result.output
    assert (target / "photo.jpg").exists()
    assert not (target / "images").exists()


def test_conflict_renames_moved_file(tmp_path):
    target = _make_target(tmp_path)
    images_dir = target / "images"
    images_dir.mkdir()
    (images_dir / "photo.jpg").write_text("already here", encoding="utf-8")

    result = runner.invoke(app, [str(target)])
    assert result.exit_code == 0, result.output

    assert (images_dir / "photo.jpg").read_text(encoding="utf-8") == "already here"
    assert (images_dir / "photo (1).jpg").read_text(encoding="utf-8") == "img"


def test_ignored_filenames_are_left_in_place(tmp_path):
    target = _make_target(tmp_path)
    (target / "Thumbs.db").write_text("system file", encoding="utf-8")

    result = runner.invoke(app, [str(target)])
    assert result.exit_code == 0, result.output

    assert (target / "Thumbs.db").exists()


def test_existing_subdirectories_are_not_touched(tmp_path):
    target = _make_target(tmp_path)
    sub = target / "keep_me"
    sub.mkdir()
    (sub / "inner.jpg").write_text("nested", encoding="utf-8")

    result = runner.invoke(app, [str(target)])
    assert result.exit_code == 0, result.output

    assert (sub / "inner.jpg").read_text(encoding="utf-8") == "nested"


def test_rerun_is_idempotent(tmp_path):
    target = _make_target(tmp_path)
    runner.invoke(app, [str(target)])

    result = runner.invoke(app, [str(target)])
    assert result.exit_code == 0, result.output
    assert "Nothing to organize" in result.output


def test_custom_config_overrides_categories(tmp_path):
    target = _make_target(tmp_path)
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(
        "categories:\n"
        "  weird: [jpg]\n"
        "default_category: leftovers\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, [str(target), "--config", str(rules_file)])
    assert result.exit_code == 0, result.output

    assert (target / "weird" / "photo.jpg").exists()
    assert (target / "leftovers" / "report.pdf").exists()
    assert (target / "leftovers" / "notes.xyz").exists()


def test_target_not_a_directory_fails(tmp_path):
    missing = tmp_path / "does_not_exist"
    result = runner.invoke(app, [str(missing)])
    assert result.exit_code == 1
    assert "Not a directory" in result.output


def test_real_run_appends_log(devtoolbox_home, tmp_path):
    target = _make_target(tmp_path)

    result = runner.invoke(app, [str(target)])
    assert result.exit_code == 0, result.output

    log_path = orgdir_log_path()
    assert log_path.exists()
    log_text = log_path.read_text(encoding="utf-8")
    assert "photo.jpg -> images/photo.jpg" in log_text


def test_dry_run_does_not_write_log(devtoolbox_home, tmp_path):
    target = _make_target(tmp_path)

    result = runner.invoke(app, [str(target), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert not orgdir_log_path().exists()
