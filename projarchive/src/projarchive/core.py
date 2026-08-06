from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from projarchive import marker

VENV_DIR_NAMES = ("venv", ".venv")

_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


class VenvNotFoundError(RuntimeError):
    """No venv/.venv directory found under the project."""


class AlreadyArchivedError(RuntimeError):
    """Project already has an .archived marker."""


class PipFreezeError(RuntimeError):
    """`pip freeze` failed while generating requirements.txt."""


class RequirementsNotFoundError(RuntimeError):
    """No requirements.txt found under the project."""


class VenvAlreadyExistsError(RuntimeError):
    """Project already has a venv/.venv directory."""


class RestoreError(RuntimeError):
    """`uv`/`python -m venv` or the dependency install step failed."""


def human_size(num_bytes: float) -> str:
    """Format a byte count as a human-readable string, e.g. `1.23 GB`."""
    size = float(num_bytes)
    for unit in _UNITS:
        if unit == "B":
            if size < 1024:
                return f"{size:.0f} {unit}"
        elif size < 1024 or unit == _UNITS[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} {_UNITS[-1]}"


def find_venv_dir(project: Path) -> Optional[Path]:
    for name in VENV_DIR_NAMES:
        candidate = project / name
        if candidate.is_dir():
            return candidate
    return None


def dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def pip_executable(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "pip.exe"
    return venv_dir / "bin" / "pip"


def ensure_requirements(project: Path, venv_dir: Path) -> tuple[Path, bool]:
    """Return (requirements.txt path, whether it was just generated).

    Raises PipFreezeError if requirements.txt doesn't exist and `pip freeze`
    fails, so the caller can abort before deleting the venv.
    """
    req_path = project / "requirements.txt"
    if req_path.exists():
        return req_path, False

    pip = pip_executable(venv_dir)
    try:
        result = subprocess.run(
            [str(pip), "freeze"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise PipFreezeError(f"pip freeze failed for {project}: {exc}") from exc

    req_path.write_text(result.stdout, encoding="utf-8")
    return req_path, True


@dataclass
class ArchiveResult:
    project: Path
    venv_dir_name: str
    venv_size_bytes: int
    requirements_generated: bool
    dry_run: bool = False


def archive_project(project: Path, *, dry_run: bool = False) -> ArchiveResult:
    if marker.is_archived(project):
        raise AlreadyArchivedError(f"{project} is already archived")

    venv_dir = find_venv_dir(project)
    if venv_dir is None:
        raise VenvNotFoundError(f"No venv/.venv found under {project}")

    size = dir_size(venv_dir)

    if dry_run:
        # No side effects in dry-run mode: don't touch pip, don't delete anything.
        would_generate = not (project / "requirements.txt").exists()
        return ArchiveResult(
            project=project,
            venv_dir_name=venv_dir.name,
            venv_size_bytes=size,
            requirements_generated=would_generate,
            dry_run=True,
        )

    # Raises PipFreezeError before anything is deleted if generation fails.
    _req_path, generated = ensure_requirements(project, venv_dir)

    shutil.rmtree(venv_dir)
    marker.write_marker(project, venv_dir_name=venv_dir.name)

    return ArchiveResult(
        project=project,
        venv_dir_name=venv_dir.name,
        venv_size_bytes=size,
        requirements_generated=generated,
        dry_run=False,
    )


def uv_available() -> bool:
    return shutil.which("uv") is not None


def _run(cmd: list[str], *, cwd: Path) -> None:
    try:
        subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RestoreError(f"command failed ({' '.join(cmd)}): {exc}") from exc


@dataclass
class RestoreResult:
    project: Path
    venv_dir_name: str
    used_uv: bool
    elapsed_seconds: float


def restore_project(project: Path) -> RestoreResult:
    req_path = project / "requirements.txt"
    if not req_path.exists():
        raise RequirementsNotFoundError(f"requirements.txt not found under {project}")

    if find_venv_dir(project) is not None:
        raise VenvAlreadyExistsError(f"{project} already has a venv")

    start = time.monotonic()
    used_uv = uv_available()
    if used_uv:
        _run(["uv", "venv"], cwd=project)
        _run(["uv", "pip", "install", "-r", str(req_path)], cwd=project)
        venv_dir_name = ".venv"
    else:
        _run([sys.executable, "-m", "venv", "venv"], cwd=project)
        pip = pip_executable(project / "venv")
        _run([str(pip), "install", "-r", str(req_path)], cwd=project)
        venv_dir_name = "venv"
    elapsed = time.monotonic() - start

    marker.remove_marker(project)

    return RestoreResult(
        project=project,
        venv_dir_name=venv_dir_name,
        used_uv=used_uv,
        elapsed_seconds=elapsed,
    )


def iter_project_dirs(parent: Path) -> list[Path]:
    return sorted((p for p in parent.iterdir() if p.is_dir()), key=lambda p: p.name)


@dataclass
class ProjectStatus:
    name: str
    path: Path
    status: str  # "active" | "archived" | "unarchived"
    venv_dir_name: Optional[str]
    venv_size_bytes: Optional[int]
    has_requirements: bool


def get_project_status(project: Path) -> Optional[ProjectStatus]:
    """Return this project's status, or None if PROJECT doesn't look like a project at all."""
    venv_dir = find_venv_dir(project)
    archived = marker.is_archived(project)
    has_requirements = (project / "requirements.txt").exists()

    if venv_dir is None and not archived and not has_requirements:
        return None

    if venv_dir is not None:
        status = "active"
        venv_dir_name = venv_dir.name
        venv_size_bytes = dir_size(venv_dir)
    elif archived:
        status = "archived"
        stored = marker.read_marker(project)
        venv_dir_name = stored.venv_dir_name if stored else None
        venv_size_bytes = None
    else:
        status = "unarchived"
        venv_dir_name = None
        venv_size_bytes = None

    return ProjectStatus(
        name=project.name,
        path=project,
        status=status,
        venv_dir_name=venv_dir_name,
        venv_size_bytes=venv_size_bytes,
        has_requirements=has_requirements,
    )


def list_projects(parent: Path) -> list[ProjectStatus]:
    statuses = (get_project_status(p) for p in iter_project_dirs(parent))
    return [s for s in statuses if s is not None]
