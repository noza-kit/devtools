from __future__ import annotations

import shutil
import tarfile
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from projarchive import core, db, paths
from projarchive.readme_gen import ensure_readme
from projarchive.scan import LargeFile

VALID_FORMATS = ("zip", "tar.gz")
VALID_LEVELS = ("standard", "max")

_ZIP_COMPRESSLEVEL = {"standard": 6, "max": 9}
_GZIP_COMPRESSLEVEL = {"standard": 6, "max": 9}

EXCLUDED_DIR_SUFFIX = "_excluded"


class ArchiveAlreadyExistsError(RuntimeError):
    """The target archive filename already exists."""


class IntegrityCheckError(RuntimeError):
    """The freshly-written archive failed to verify."""


class ArchiveNotFoundError(RuntimeError):
    """The given archive file does not exist."""


class DestinationExistsError(RuntimeError):
    """Restore target directory already exists."""


class UnrecognizedArchiveError(ValueError):
    """Archive filename doesn't end in .zip or .tar.gz."""


def _archive_filename(project_name: str, fmt: str) -> str:
    date_str = datetime.now().strftime("%Y%m%d")
    ext = "zip" if fmt == "zip" else "tar.gz"
    return f"{project_name}_{date_str}.{ext}"


def _move_excluded_files(project: Path, excluded: list[LargeFile]) -> Optional[Path]:
    if not excluded:
        return None
    excluded_dir = project.parent / f"{project.name}{EXCLUDED_DIR_SUFFIX}"
    excluded_dir.mkdir(parents=True, exist_ok=True)
    for lf in excluded:
        rel = lf.path.relative_to(project)
        dest = excluded_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(lf.path), str(dest))
    return excluded_dir


def _make_zip(project: Path, archive_path: Path, level: str) -> None:
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=_ZIP_COMPRESSLEVEL[level]
    ) as zf:
        for f in sorted(project.rglob("*")):
            if f.is_file():
                zf.write(f, arcname=str(Path(project.name) / f.relative_to(project)))


def _make_tar_gz(project: Path, archive_path: Path, level: str) -> None:
    with tarfile.open(archive_path, mode="w:gz", compresslevel=_GZIP_COMPRESSLEVEL[level]) as tf:
        tf.add(project, arcname=project.name)


def _verify_zip(archive_path: Path) -> bool:
    try:
        with zipfile.ZipFile(archive_path) as zf:
            return zf.testzip() is None
    except (zipfile.BadZipFile, OSError):
        return False


def _verify_tar_gz(archive_path: Path) -> bool:
    try:
        with tarfile.open(archive_path, mode="r:gz") as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                extracted = tf.extractfile(member)
                if extracted is None:
                    return False
                while extracted.read(1024 * 1024):
                    pass
        return True
    except (tarfile.TarError, OSError):
        return False


def _extractall(tf: tarfile.TarFile, dest_parent: Path) -> None:
    try:
        tf.extractall(dest_parent, filter="data")
    except TypeError:
        # Python < 3.12 doesn't support the `filter` kwarg.
        tf.extractall(dest_parent)


@dataclass
class CompressResult:
    project: Path
    archive_path: Path
    format: str
    compression_level: str
    original_size_bytes: int
    compressed_size_bytes: int
    venv_stripped: bool
    venv_dir_name: Optional[str]
    venv_size_bytes: Optional[int]
    requirements_generated: Optional[bool]
    readme_generated: bool
    excluded_files: list[LargeFile]
    excluded_dir: Optional[Path]
    compression_id: int


def compress_project(
    project: Path,
    *,
    format: str = "zip",
    compression_level: str = "standard",
    excluded_files: Optional[list[LargeFile]] = None,
    db_path: Optional[Path] = None,
) -> CompressResult:
    if format not in VALID_FORMATS:
        raise ValueError(f"Unsupported format: {format}")
    if compression_level not in VALID_LEVELS:
        raise ValueError(f"Unsupported compression level: {compression_level}")

    excluded_files = excluded_files or []
    project = project.resolve()

    original_size_bytes = core.dir_size(project)

    archive_path = project.parent / _archive_filename(project.name, format)
    if archive_path.exists():
        raise ArchiveAlreadyExistsError(f"{archive_path} already exists")

    venv_stripped = False
    venv_dir_name: Optional[str] = None
    venv_size_bytes: Optional[int] = None
    requirements_generated: Optional[bool] = None

    if core.find_venv_dir(project) is not None:
        archive_result = core.archive_project(project)
        venv_stripped = True
        venv_dir_name = archive_result.venv_dir_name
        venv_size_bytes = archive_result.venv_size_bytes
        requirements_generated = archive_result.requirements_generated

    _readme_path, readme_generated = ensure_readme(project)

    excluded_meta = [
        {"path": str(lf.path.relative_to(project)), "size_bytes": lf.size_bytes} for lf in excluded_files
    ]
    excluded_dir = _move_excluded_files(project, excluded_files)

    try:
        if format == "zip":
            _make_zip(project, archive_path, compression_level)
        else:
            _make_tar_gz(project, archive_path, compression_level)
    except Exception:
        archive_path.unlink(missing_ok=True)
        raise

    verify_fn = _verify_zip if format == "zip" else _verify_tar_gz
    if not verify_fn(archive_path):
        archive_path.unlink(missing_ok=True)
        raise IntegrityCheckError(
            f"Integrity check failed for {archive_path}; original project was left in place"
        )

    compressed_size_bytes = archive_path.stat().st_size

    shutil.rmtree(project)

    conn = db.get_connection(db_path or paths.compressed_db_path())
    try:
        compression_id = db.insert_compression(
            conn,
            project_name=project.name,
            parent_dir=str(project.parent),
            archive_path=str(archive_path),
            format=format,
            compression_level=compression_level,
            original_size_bytes=original_size_bytes,
            compressed_size_bytes=compressed_size_bytes,
            venv_stripped=venv_stripped,
            venv_dir_name=venv_dir_name,
            excluded_files=excluded_meta,
            excluded_dir=str(excluded_dir) if excluded_dir else None,
        )
    finally:
        conn.close()

    return CompressResult(
        project=project,
        archive_path=archive_path,
        format=format,
        compression_level=compression_level,
        original_size_bytes=original_size_bytes,
        compressed_size_bytes=compressed_size_bytes,
        venv_stripped=venv_stripped,
        venv_dir_name=venv_dir_name,
        venv_size_bytes=venv_size_bytes,
        requirements_generated=requirements_generated,
        readme_generated=readme_generated,
        excluded_files=excluded_files,
        excluded_dir=excluded_dir,
        compression_id=compression_id,
    )


def _derive_project_name(archive_path: Path) -> str:
    stem = archive_path.name[: -len(".tar.gz")] if archive_path.name.endswith(".tar.gz") else archive_path.stem
    parts = stem.rsplit("_", 1)
    if len(parts) == 2 and len(parts[1]) == 8 and parts[1].isdigit():
        return parts[0]
    return stem


@dataclass
class RestoreResult:
    archive_path: Path
    project: Path
    elapsed_seconds: float
    excluded_restored: int
    venv_attempted: bool
    venv_rebuilt: bool
    used_uv: Optional[bool]
    venv_error: Optional[str]
    compression_id: Optional[int]


def restore_compressed_project(
    archive_path: Path,
    *,
    db_path: Optional[Path] = None,
) -> RestoreResult:
    archive_path = archive_path.resolve()
    if not archive_path.exists():
        raise ArchiveNotFoundError(f"{archive_path} not found")

    if archive_path.name.endswith(".tar.gz"):
        fmt = "tar.gz"
    elif archive_path.suffix == ".zip":
        fmt = "zip"
    else:
        raise UnrecognizedArchiveError(f"Unrecognized archive extension: {archive_path.name}")

    conn = db.get_connection(db_path or paths.compressed_db_path())
    try:
        record = db.get_by_archive_path(conn, str(archive_path))

        if record is not None:
            project_name = record.project_name
            dest_parent = Path(record.parent_dir)
        else:
            project_name = _derive_project_name(archive_path)
            dest_parent = archive_path.parent

        project = dest_parent / project_name
        if project.exists():
            raise DestinationExistsError(f"{project} already exists; refusing to overwrite")

        start = time.monotonic()

        if fmt == "zip":
            with zipfile.ZipFile(archive_path) as zf:
                zf.extractall(dest_parent)
        else:
            with tarfile.open(archive_path, mode="r:gz") as tf:
                _extractall(tf, dest_parent)

        excluded_restored = 0
        if record is not None and record.excluded_dir:
            excluded_dir = Path(record.excluded_dir)
            if excluded_dir.is_dir():
                for item in excluded_dir.rglob("*"):
                    if not item.is_file():
                        continue
                    dest = project / item.relative_to(excluded_dir)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(dest))
                    excluded_restored += 1
                shutil.rmtree(excluded_dir, ignore_errors=True)

        venv_attempted = False
        venv_rebuilt = False
        used_uv: Optional[bool] = None
        venv_error: Optional[str] = None

        if (project / "requirements.txt").exists() and core.find_venv_dir(project) is None:
            venv_attempted = True
            try:
                venv_result = core.restore_project(project)
                venv_rebuilt = True
                used_uv = venv_result.used_uv
            except core.RestoreError as exc:
                venv_error = str(exc)

        elapsed = time.monotonic() - start

        compression_id = None
        if record is not None:
            compression_id = record.id
            db.mark_restored(
                conn,
                record.id,
                elapsed_seconds=elapsed,
                venv_rebuilt=venv_rebuilt if venv_attempted else None,
                used_uv=used_uv,
            )
    finally:
        conn.close()

    return RestoreResult(
        archive_path=archive_path,
        project=project,
        elapsed_seconds=elapsed,
        excluded_restored=excluded_restored,
        venv_attempted=venv_attempted,
        venv_rebuilt=venv_rebuilt,
        used_uv=used_uv,
        venv_error=venv_error,
        compression_id=compression_id,
    )


def list_compressed(parent: Path, *, db_path: Optional[Path] = None) -> list[db.Compression]:
    """Compressed-project records under PARENT whose archive file still exists on disk."""
    parent = parent.resolve()
    conn = db.get_connection(db_path or paths.compressed_db_path())
    try:
        records = db.list_active_compressions(conn, str(parent))
    finally:
        conn.close()
    return [r for r in records if Path(r.archive_path).exists()]
