from __future__ import annotations

import shutil
import subprocess
import tarfile
import zipfile
from datetime import datetime

import pytest

from projarchive import compress, db, paths, scan


def _get_record(archive_path):
    conn = db.get_connection(paths.compressed_db_path())
    try:
        return db.get_by_archive_path(conn, str(archive_path))
    finally:
        conn.close()


# --- compress_project -------------------------------------------------------


def test_compress_project_strips_venv_and_creates_zip(project, monkeypatch, projarchive_home):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="pytest==8.0.0\n", stderr=""),
    )
    (project / "main.py").write_text("print('hi')\n", encoding="utf-8")

    result = compress.compress_project(project, format="zip")

    assert result.venv_stripped is True
    assert result.venv_dir_name == ".venv"
    assert result.readme_generated is True
    assert not project.exists()
    assert result.archive_path.suffix == ".zip"
    assert result.archive_path.exists()

    with zipfile.ZipFile(result.archive_path) as zf:
        names = zf.namelist()
    assert any(n.endswith("main.py") for n in names)
    assert any(n.endswith("requirements.txt") for n in names)
    assert any(n.endswith("README.md") for n in names)
    assert not any(".venv" in n for n in names)


def test_compress_project_tar_gz_format(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("hello", encoding="utf-8")

    result = compress.compress_project(proj, format="tar.gz")

    assert result.archive_path.name.endswith(".tar.gz")
    with tarfile.open(result.archive_path, "r:gz") as tf:
        names = tf.getnames()
    assert any(n.endswith("a.txt") for n in names)


def test_compress_project_leaves_existing_readme_alone(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "README.md").write_text("already here\n", encoding="utf-8")

    result = compress.compress_project(proj)

    assert result.readme_generated is False


def test_compress_project_moves_excluded_files_to_sibling_dir(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "small.txt").write_bytes(b"x" * 10)
    big = proj / "dataset.bin"
    big.write_bytes(b"x" * 1000)

    excluded = [scan.LargeFile(path=big, size_bytes=1000)]
    result = compress.compress_project(proj, excluded_files=excluded)

    excluded_dir = tmp_path / "proj_excluded"
    assert excluded_dir.is_dir()
    assert (excluded_dir / "dataset.bin").read_bytes() == b"x" * 1000
    assert result.excluded_dir == excluded_dir
    assert not proj.exists()

    with zipfile.ZipFile(result.archive_path) as zf:
        names = zf.namelist()
    assert not any("dataset.bin" in n for n in names)
    assert any(n.endswith("small.txt") for n in names)


def test_compress_project_raises_if_archive_already_exists(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")
    date_str = datetime.now().strftime("%Y%m%d")
    (tmp_path / f"proj_{date_str}.zip").write_bytes(b"existing")

    with pytest.raises(compress.ArchiveAlreadyExistsError):
        compress.compress_project(proj)

    assert proj.exists()


def test_compress_project_keeps_original_on_integrity_failure(tmp_path, monkeypatch, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")

    monkeypatch.setattr(compress, "_verify_zip", lambda archive_path: False)

    with pytest.raises(compress.IntegrityCheckError):
        compress.compress_project(proj)

    assert proj.exists()
    assert not list(tmp_path.glob("*.zip"))


def test_compress_project_records_metadata(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")

    result = compress.compress_project(proj, format="zip", compression_level="max")

    record = _get_record(result.archive_path)
    assert record is not None
    assert record.status == "compressed"
    assert record.project_name == "proj"
    assert record.compression_level == "max"
    assert record.compressed_size_bytes == result.compressed_size_bytes
    assert record.original_size_bytes == result.original_size_bytes


# --- restore_compressed_project ---------------------------------------------


def test_restore_compressed_project_extracts_and_rebuilds_venv(tmp_path, monkeypatch, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (proj / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")

    compress_result = compress.compress_project(proj)

    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/uv" if name == "uv" else None)
    calls = []
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda cmd, **k: calls.append(cmd) or subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""),
    )

    restore_result = compress.restore_compressed_project(compress_result.archive_path)

    assert restore_result.project == proj
    assert proj.exists()
    assert (proj / "main.py").read_text(encoding="utf-8") == "print('hi')\n"
    assert restore_result.venv_attempted is True
    assert restore_result.venv_rebuilt is True
    assert restore_result.used_uv is True
    assert calls[0] == ["uv", "venv"]

    record = _get_record(compress_result.archive_path)
    assert record.status == "restored"
    assert record.restore_used_uv is True


def test_restore_compressed_project_restores_excluded_files(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "small.txt").write_text("x", encoding="utf-8")
    big = proj / "dataset.bin"
    big.write_bytes(b"x" * 1000)

    excluded = [scan.LargeFile(path=big, size_bytes=1000)]
    compress_result = compress.compress_project(proj, excluded_files=excluded)

    restore_result = compress.restore_compressed_project(compress_result.archive_path)

    assert restore_result.excluded_restored == 1
    assert (proj / "dataset.bin").stat().st_size == 1000
    assert not (tmp_path / "proj_excluded").exists()


def test_restore_compressed_project_no_venv_rebuild_when_no_requirements(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")

    compress_result = compress.compress_project(proj)
    restore_result = compress.restore_compressed_project(compress_result.archive_path)

    assert restore_result.venv_attempted is False
    assert restore_result.venv_rebuilt is False


def test_restore_compressed_project_tar_gz_round_trip(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("hello", encoding="utf-8")

    compress_result = compress.compress_project(proj, format="tar.gz")
    restore_result = compress.restore_compressed_project(compress_result.archive_path)

    assert (proj / "a.txt").read_text(encoding="utf-8") == "hello"
    assert restore_result.project == proj


def test_restore_compressed_project_raises_if_destination_exists(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")
    result = compress.compress_project(proj)

    proj.mkdir()

    with pytest.raises(compress.DestinationExistsError):
        compress.restore_compressed_project(result.archive_path)


def test_restore_compressed_project_raises_if_archive_missing(tmp_path, projarchive_home):
    with pytest.raises(compress.ArchiveNotFoundError):
        compress.restore_compressed_project(tmp_path / "missing.zip")


def test_restore_compressed_project_falls_back_without_metadata(tmp_path, projarchive_home):
    """A compressed project whose DB record is gone still restores, from the filename."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")
    result = compress.compress_project(proj)

    conn = db.get_connection(paths.compressed_db_path())
    conn.execute("DELETE FROM compressions")
    conn.commit()
    conn.close()

    restore_result = compress.restore_compressed_project(result.archive_path)

    assert restore_result.project == proj
    assert (proj / "a.txt").exists()
    assert restore_result.compression_id is None


# --- list_compressed ----------------------------------------------------------


def test_list_compressed_only_returns_records_whose_archive_still_exists(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")
    result = compress.compress_project(proj)

    found = compress.list_compressed(tmp_path)
    assert len(found) == 1
    assert found[0].project_name == "proj"

    result.archive_path.unlink()
    assert compress.list_compressed(tmp_path) == []


def test_list_compressed_excludes_restored_projects(tmp_path, projarchive_home):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "a.txt").write_text("x", encoding="utf-8")
    result = compress.compress_project(proj)

    compress.restore_compressed_project(result.archive_path)

    assert compress.list_compressed(tmp_path) == []
