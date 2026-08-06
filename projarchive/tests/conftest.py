from __future__ import annotations

import pytest

from projarchive import marker


def _make_venv(venv_dir):
    (venv_dir / "lib").mkdir(parents=True)
    (venv_dir / "lib" / "a.txt").write_bytes(b"x" * 20)
    (venv_dir / "pyvenv.cfg").write_bytes(b"x" * 10)
    return venv_dir


@pytest.fixture
def project(tmp_path):
    """A project dir with a `.venv` (30 bytes total) and no requirements.txt."""
    proj = tmp_path / "myproject"
    _make_venv(proj / ".venv")
    return proj


@pytest.fixture
def project_with_requirements(tmp_path):
    """A project dir with a `venv` and a pre-existing requirements.txt."""
    proj = tmp_path / "myproject"
    _make_venv(proj / "venv")
    (proj / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    return proj


@pytest.fixture
def archived_project(tmp_path):
    """A project dir with requirements.txt and an .archived marker, no venv."""
    proj = tmp_path / "myproject"
    proj.mkdir()
    (proj / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    marker.write_marker(proj, venv_dir_name=".venv")
    return proj
