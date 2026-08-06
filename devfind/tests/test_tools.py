from __future__ import annotations

import pytest

from devfind.tools import (
    MissingToolError,
    ensure_required_tools,
    find_missing_required_tools,
    is_bat_available,
)


def _patch_which(monkeypatch, available: set[str]):
    monkeypatch.setattr("devfind.tools.shutil.which", lambda name: f"/usr/bin/{name}" if name in available else None)


def test_find_missing_required_tools_none_missing(monkeypatch):
    _patch_which(monkeypatch, {"fd", "rg", "fzf"})

    assert find_missing_required_tools() == []


def test_find_missing_required_tools_reports_missing(monkeypatch):
    _patch_which(monkeypatch, {"fd", "fzf"})

    assert find_missing_required_tools() == ["rg"]


def test_ensure_required_tools_raises_with_install_hint(monkeypatch):
    _patch_which(monkeypatch, {"fzf"})

    with pytest.raises(MissingToolError) as exc_info:
        ensure_required_tools()

    error = exc_info.value
    assert error.missing == ["fd", "rg"]
    assert "fd" in str(error)
    assert "rg" in str(error)
    assert "winget" in str(error) or "brew" in str(error)


def test_ensure_required_tools_passes_when_all_present(monkeypatch):
    _patch_which(monkeypatch, {"fd", "rg", "fzf"})

    ensure_required_tools()  # should not raise


def test_is_bat_available_true(monkeypatch):
    _patch_which(monkeypatch, {"bat"})

    assert is_bat_available() is True


def test_is_bat_available_false(monkeypatch):
    _patch_which(monkeypatch, set())

    assert is_bat_available() is False
