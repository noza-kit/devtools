from __future__ import annotations

import shutil
import subprocess

from typer.testing import CliRunner

from projarchive import marker
from projarchive.cli import app

runner = CliRunner()


def test_archive_project_cmd_missing_dir_fails(tmp_path):
    result = runner.invoke(app, ["archive-project", str(tmp_path / "missing")])
    assert result.exit_code == 1
    assert "not a directory" in result.output.lower()


def test_archive_project_cmd_no_venv_fails(tmp_path):
    result = runner.invoke(app, ["archive-project", str(tmp_path)])
    assert result.exit_code == 1
    assert "no venv" in result.output.lower()


def test_archive_project_cmd_generates_requirements_and_deletes_venv(project, monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="pytest==8.0.0\n", stderr=""),
    )

    result = runner.invoke(app, ["archive-project", str(project)])

    assert result.exit_code == 0, result.output
    assert "generated via" in result.output.lower()
    assert not (project / ".venv").exists()
    assert marker.is_archived(project)


def test_archive_project_cmd_reuses_existing_requirements(project_with_requirements, monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("pip should not be invoked when requirements.txt exists")

    monkeypatch.setattr(subprocess, "run", _boom)

    result = runner.invoke(app, ["archive-project", str(project_with_requirements)])

    assert result.exit_code == 0, result.output
    assert "already existed" in result.output.lower()


def test_archive_project_cmd_pip_failure_keeps_venv(project, monkeypatch):
    def _fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(subprocess, "run", _fail)

    result = runner.invoke(app, ["archive-project", str(project)])

    assert result.exit_code == 1
    assert "aborted" in result.output.lower()
    assert (project / ".venv").exists()


def test_archive_project_cmd_already_archived_fails(project_with_requirements, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    marker.write_marker(project_with_requirements, venv_dir_name="venv")

    result = runner.invoke(app, ["archive-project", str(project_with_requirements)])

    assert result.exit_code == 1
    assert "already archived" in result.output.lower()


def test_restore_project_cmd_missing_requirements_fails(tmp_path):
    result = runner.invoke(app, ["restore-project", str(tmp_path)])
    assert result.exit_code == 1
    assert "requirements.txt" in result.output.lower()


def test_restore_project_cmd_already_restored_is_noop(project_with_requirements):
    result = runner.invoke(app, ["restore-project", str(project_with_requirements)])
    assert result.exit_code == 0
    assert "already restored" in result.output.lower()


def test_restore_project_cmd_success_with_uv(archived_project, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    )

    result = runner.invoke(app, ["restore-project", str(archived_project)])

    assert result.exit_code == 0, result.output
    assert "via uv" in result.output.lower()
    assert not marker.is_archived(archived_project)


def test_restore_project_cmd_falls_back_without_uv(archived_project, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    )

    result = runner.invoke(app, ["restore-project", str(archived_project)])

    assert result.exit_code == 0, result.output
    assert "python -m venv" in result.output.lower()


def test_restore_project_cmd_failure_keeps_marker(archived_project, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)

    def _fail(cmd, **k):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", _fail)

    result = runner.invoke(app, ["restore-project", str(archived_project)])

    assert result.exit_code == 1
    assert marker.is_archived(archived_project)


def test_archive_project_cmd_all_archives_every_project_under_parent(tmp_path, monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, stdout="pytest==8.0.0\n", stderr=""),
    )

    proj_a = tmp_path / "proj_a"
    (proj_a / ".venv" / "lib").mkdir(parents=True)
    (proj_a / ".venv" / "lib" / "a.txt").write_bytes(b"x" * 10)

    proj_b = tmp_path / "proj_b"
    (proj_b / "venv" / "lib").mkdir(parents=True)
    (proj_b / "venv" / "lib" / "a.txt").write_bytes(b"x" * 10)

    not_a_project = tmp_path / "not_a_project"
    not_a_project.mkdir()

    result = runner.invoke(app, ["archive-project", str(tmp_path), "--all"])

    assert result.exit_code == 0, result.output
    assert marker.is_archived(proj_a)
    assert marker.is_archived(proj_b)
    assert not marker.is_archived(not_a_project)
    assert "2 project(s) archived" in result.output
    assert "1 skipped" in result.output


def test_archive_project_cmd_all_skips_already_archived(archived_project, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))

    result = runner.invoke(app, ["archive-project", str(archived_project.parent), "--all"])

    assert result.exit_code == 0, result.output
    assert "already archived" in result.output.lower()
    assert "0 project(s) archived, 1 skipped" in result.output


def test_archive_project_cmd_dry_run_does_not_delete_venv(project, monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("dry-run must not invoke pip")

    monkeypatch.setattr(subprocess, "run", _boom)

    result = runner.invoke(app, ["archive-project", str(project), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "would archive" in result.output.lower()
    assert (project / ".venv").exists()
    assert not (project / "requirements.txt").exists()
    assert not marker.is_archived(project)


def test_archive_project_cmd_all_dry_run_does_not_delete_any_venv(tmp_path, monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("dry-run must not invoke pip")

    monkeypatch.setattr(subprocess, "run", _boom)

    proj_a = tmp_path / "proj_a"
    (proj_a / ".venv" / "lib").mkdir(parents=True)
    (proj_a / ".venv" / "lib" / "a.txt").write_bytes(b"x" * 10)

    result = runner.invoke(app, ["archive-project", str(tmp_path), "--all", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "would be archived" in result.output.lower()
    assert (proj_a / ".venv").exists()
    assert not marker.is_archived(proj_a)


def test_list_projects_cmd_shows_active_and_archived_projects(tmp_path):
    proj_a = tmp_path / "proj_a"
    (proj_a / "venv" / "lib").mkdir(parents=True)
    (proj_a / "venv" / "lib" / "a.txt").write_bytes(b"x" * 10)

    proj_b = tmp_path / "proj_b"
    proj_b.mkdir()
    (proj_b / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    marker.write_marker(proj_b, venv_dir_name="venv")

    result = runner.invoke(app, ["list-projects", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "proj_a" in result.output
    assert "proj_b" in result.output
    assert "active" in result.output
    assert "archived" in result.output


def test_list_projects_cmd_missing_dir_fails(tmp_path):
    result = runner.invoke(app, ["list-projects", str(tmp_path / "missing")])
    assert result.exit_code == 1


def test_list_projects_cmd_empty_parent_reports_cleanly(tmp_path):
    result = runner.invoke(app, ["list-projects", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "no projects found" in result.output.lower()
