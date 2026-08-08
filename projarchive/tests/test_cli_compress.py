from __future__ import annotations

import subprocess
import zipfile

from typer.testing import CliRunner

from projarchive.cli import app

runner = CliRunner()


def test_compress_project_cmd_missing_dir_fails(tmp_path, projarchive_home):
    result = runner.invoke(app, ["compress-project", str(tmp_path / "missing")])
    assert result.exit_code == 1
    assert "not a directory" in result.output.lower()


def test_compress_project_cmd_rejects_bad_format(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")

    result = runner.invoke(app, ["compress-project", str(proj), "--format", "rar"])

    assert result.exit_code == 1
    assert "unsupported format" in result.output.lower()


def test_compress_project_cmd_dry_run_does_not_delete(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")

    result = runner.invoke(app, ["compress-project", str(proj), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "would compress" in result.output.lower()
    assert proj.exists()
    assert not list(tmp_path.glob("*.zip"))


def test_compress_project_cmd_creates_zip_and_deletes_original(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")

    result = runner.invoke(app, ["compress-project", str(proj)])

    assert result.exit_code == 0, result.output
    assert "compressed" in result.output.lower()
    assert not proj.exists()
    assert len(list(tmp_path.glob("*.zip"))) == 1


def test_compress_project_cmd_max_compression_shortcut(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")

    result = runner.invoke(app, ["compress-project", str(proj), "--max-compression"])

    assert result.exit_code == 0, result.output


def test_compress_project_cmd_large_file_excluded_via_flag(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "dataset.bin").write_bytes(b"x" * 1000)

    result = runner.invoke(
        app,
        [
            "compress-project",
            str(proj),
            "--large-file-threshold-mb",
            "0",
            "--exclude-large-files",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "excluding 1 file" in result.output.lower()
    assert (tmp_path / "proj_excluded" / "dataset.bin").exists()


def test_compress_project_cmd_large_file_excluded_via_relative_path(tmp_path, projarchive_home, monkeypatch):
    """Regression: excluding files must work when PATH is given relative, not just absolute."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "dataset.bin").write_bytes(b"x" * 1000)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "compress-project",
            "proj",
            "--large-file-threshold-mb",
            "0",
            "--exclude-large-files",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "proj_excluded" / "dataset.bin").exists()


def test_compress_project_cmd_large_file_included_via_flag(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "dataset.bin").write_bytes(b"x" * 1000)

    result = runner.invoke(
        app,
        [
            "compress-project",
            str(proj),
            "--large-file-threshold-mb",
            "0",
            "--include-large-files",
        ],
    )

    assert result.exit_code == 0, result.output
    archive = next(tmp_path.glob("*.zip"))
    with zipfile.ZipFile(archive) as zf:
        assert any("dataset.bin" in n for n in zf.namelist())


def test_compress_project_cmd_non_interactive_without_flag_fails(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "dataset.bin").write_bytes(b"x" * 1000)

    result = runner.invoke(app, ["compress-project", str(proj), "--large-file-threshold-mb", "0"])

    assert result.exit_code == 1
    assert proj.exists()


def test_restore_compressed_project_cmd_round_trip(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("hello", encoding="utf-8")
    runner.invoke(app, ["compress-project", str(proj)])
    archive = next(tmp_path.glob("*.zip"))

    result = runner.invoke(app, ["restore-compressed-project", str(archive)])

    assert result.exit_code == 0, result.output
    assert "restored" in result.output.lower()
    assert (proj / "a.txt").read_text(encoding="utf-8") == "hello"


def test_restore_compressed_project_cmd_missing_file_fails(tmp_path, projarchive_home):
    result = runner.invoke(app, ["restore-compressed-project", str(tmp_path / "nope.zip")])
    assert result.exit_code == 1


def test_list_projects_cmd_shows_compressed_status(tmp_path, projarchive_home, monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="pytest==8.0.0\n", stderr=""),
    )

    active = tmp_path / "active_proj"
    (active / "venv" / "lib").mkdir(parents=True)
    (active / "venv" / "lib" / "a.txt").write_bytes(b"x" * 10)

    compressed_proj = tmp_path / "compressed_proj"
    compressed_proj.mkdir()
    (compressed_proj / "a.txt").write_text("x", encoding="utf-8")
    runner.invoke(app, ["compress-project", str(compressed_proj)])

    result = runner.invoke(app, ["list-projects", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "active_proj" in result.output
    assert "compressed_proj" in result.output
    assert "compressed" in result.output.lower()
    assert not compressed_proj.exists()
