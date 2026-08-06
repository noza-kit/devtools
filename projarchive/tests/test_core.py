from __future__ import annotations

import shutil
import subprocess

import pytest

from projarchive import core, marker


def test_find_venv_dir_prefers_venv_over_dotvenv(tmp_path):
    (tmp_path / "venv").mkdir()
    (tmp_path / ".venv").mkdir()
    assert core.find_venv_dir(tmp_path).name == "venv"


def test_find_venv_dir_falls_back_to_dotvenv(tmp_path):
    (tmp_path / ".venv").mkdir()
    assert core.find_venv_dir(tmp_path).name == ".venv"


def test_find_venv_dir_returns_none_when_missing(tmp_path):
    assert core.find_venv_dir(tmp_path) is None


def test_dir_size_sums_files_recursively(project):
    assert core.dir_size(project / ".venv") == 30


def test_human_size_formats_bytes_and_larger_units():
    assert core.human_size(500) == "500 B"
    assert core.human_size(1536) == "1.50 KB"


def test_ensure_requirements_uses_existing_file_without_calling_pip(
    project_with_requirements, monkeypatch
):
    def _boom(*args, **kwargs):
        raise AssertionError("pip should not be invoked when requirements.txt exists")

    monkeypatch.setattr(subprocess, "run", _boom)

    req_path, generated = core.ensure_requirements(
        project_with_requirements, project_with_requirements / "venv"
    )

    assert generated is False
    assert req_path.read_text(encoding="utf-8") == "requests==2.31.0\n"


def test_ensure_requirements_generates_via_pip_freeze(project, monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="pytest==8.0.0\n", stderr=""),
    )

    req_path, generated = core.ensure_requirements(project, project / ".venv")

    assert generated is True
    assert req_path.read_text(encoding="utf-8") == "pytest==8.0.0\n"


def test_ensure_requirements_raises_on_pip_failure(project, monkeypatch):
    def _fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(subprocess, "run", _fail)

    with pytest.raises(core.PipFreezeError):
        core.ensure_requirements(project, project / ".venv")

    assert not (project / "requirements.txt").exists()


def test_archive_project_generates_requirements_deletes_venv_and_writes_marker(
    project, monkeypatch
):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="pytest==8.0.0\n", stderr=""),
    )

    result = core.archive_project(project)

    assert result.venv_dir_name == ".venv"
    assert result.venv_size_bytes == 30
    assert result.requirements_generated is True
    assert not (project / ".venv").exists()
    assert (project / "requirements.txt").read_text(encoding="utf-8") == "pytest==8.0.0\n"

    stored = marker.read_marker(project)
    assert stored is not None
    assert stored.venv_dir_name == ".venv"


def test_archive_project_reuses_existing_requirements(project_with_requirements, monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("pip should not be invoked when requirements.txt exists")

    monkeypatch.setattr(subprocess, "run", _boom)

    result = core.archive_project(project_with_requirements)

    assert result.requirements_generated is False
    assert not (project_with_requirements / "venv").exists()


def test_archive_project_raises_if_no_venv(tmp_path):
    with pytest.raises(core.VenvNotFoundError):
        core.archive_project(tmp_path)


def test_archive_project_raises_if_already_archived(project_with_requirements, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))
    marker.write_marker(project_with_requirements, venv_dir_name="venv")

    with pytest.raises(core.AlreadyArchivedError):
        core.archive_project(project_with_requirements)

    assert (project_with_requirements / "venv").exists()


def test_archive_project_does_not_delete_venv_on_pip_failure(project, monkeypatch):
    def _fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr(subprocess, "run", _fail)

    with pytest.raises(core.PipFreezeError):
        core.archive_project(project)

    assert (project / ".venv").exists()
    assert not marker.is_archived(project)


def test_archive_project_dry_run_does_not_touch_pip_or_delete_anything(project, monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("dry-run must not invoke pip")

    monkeypatch.setattr(subprocess, "run", _boom)

    result = core.archive_project(project, dry_run=True)

    assert result.dry_run is True
    assert result.venv_size_bytes == 30
    assert result.requirements_generated is True  # would be generated
    assert (project / ".venv").exists()
    assert not (project / "requirements.txt").exists()
    assert not marker.is_archived(project)


def test_archive_project_dry_run_reports_existing_requirements(project_with_requirements, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError()))

    result = core.archive_project(project_with_requirements, dry_run=True)

    assert result.requirements_generated is False
    assert (project_with_requirements / "venv").exists()


def test_restore_project_raises_if_no_requirements(tmp_path):
    with pytest.raises(core.RequirementsNotFoundError):
        core.restore_project(tmp_path)


def test_restore_project_raises_if_venv_already_exists(project_with_requirements):
    with pytest.raises(core.VenvAlreadyExistsError):
        core.restore_project(project_with_requirements)


def test_restore_project_uses_uv_when_available(archived_project, monkeypatch):
    calls = []
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **k: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
    )

    result = core.restore_project(archived_project)

    assert result.used_uv is True
    assert result.venv_dir_name == ".venv"
    assert calls[0] == ["uv", "venv"]
    assert calls[1][:3] == ["uv", "pip", "install"]
    assert not marker.is_archived(archived_project)


def test_restore_project_falls_back_to_venv_and_pip_when_uv_missing(archived_project, monkeypatch):
    calls = []
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **k: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
    )

    result = core.restore_project(archived_project)

    assert result.used_uv is False
    assert result.venv_dir_name == "venv"
    assert calls[0][1:3] == ["-m", "venv"]
    assert "pip" in calls[1][0].lower()
    assert not marker.is_archived(archived_project)


def test_restore_project_raises_restore_error_and_keeps_marker_on_failure(archived_project, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)

    def _fail(cmd, **k):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", _fail)

    with pytest.raises(core.RestoreError):
        core.restore_project(archived_project)

    assert marker.is_archived(archived_project)


def test_restore_project_reports_nonnegative_elapsed_time(archived_project, monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/uv")
    monkeypatch.setattr(
        subprocess, "run", lambda cmd, **k: subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    )

    result = core.restore_project(archived_project)

    assert result.elapsed_seconds >= 0


def test_iter_project_dirs_returns_immediate_subdirs_sorted(tmp_path):
    (tmp_path / "b_proj").mkdir()
    (tmp_path / "a_proj").mkdir()
    (tmp_path / "not_a_dir.txt").write_text("x", encoding="utf-8")

    dirs = core.iter_project_dirs(tmp_path)

    assert [d.name for d in dirs] == ["a_proj", "b_proj"]


def test_get_project_status_returns_none_for_non_project_dir(tmp_path):
    plain = tmp_path / "notes"
    plain.mkdir()
    assert core.get_project_status(plain) is None


def test_get_project_status_active_project(project):
    status = core.get_project_status(project)
    assert status.status == "active"
    assert status.venv_dir_name == ".venv"
    assert status.venv_size_bytes == 30
    assert status.has_requirements is False


def test_get_project_status_archived_project(archived_project):
    status = core.get_project_status(archived_project)
    assert status.status == "archived"
    assert status.venv_dir_name == ".venv"
    assert status.venv_size_bytes is None
    assert status.has_requirements is True


def test_get_project_status_unarchived_project_with_only_requirements(tmp_path):
    proj = tmp_path / "myproject"
    proj.mkdir()
    (proj / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")

    status = core.get_project_status(proj)

    assert status.status == "unarchived"
    assert status.venv_dir_name is None
    assert status.has_requirements is True


def test_list_projects_skips_non_project_dirs(tmp_path):
    parent = tmp_path
    proj_a = parent / "proj_a"
    proj_a.mkdir()
    (proj_a / "venv").mkdir()

    proj_b = parent / "proj_b"
    proj_b.mkdir()
    marker.write_marker(proj_b, venv_dir_name="venv")

    (parent / "not_a_project").mkdir()

    statuses = core.list_projects(parent)

    assert {s.name for s in statuses} == {"proj_a", "proj_b"}
    by_name = {s.name: s for s in statuses}
    assert by_name["proj_a"].status == "active"
    assert by_name["proj_b"].status == "archived"
