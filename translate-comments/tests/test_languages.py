from __future__ import annotations

import pytest

from translate_comments.languages import (
    C_FAMILY,
    PYTHON,
    SHELL,
    UnsupportedFileTypeError,
    get_profile,
)


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("app.py", PYTHON),
        ("script.PYW", PYTHON),
        ("deploy.sh", SHELL),
        ("deploy.bash", SHELL),
        ("index.js", C_FAMILY),
        ("index.tsx", C_FAMILY),
        ("main.cpp", C_FAMILY),
        ("Program.cs", C_FAMILY),
        ("Main.java", C_FAMILY),
    ],
)
def test_get_profile_by_extension(filename, expected):
    assert get_profile(filename) is expected


def test_get_profile_unsupported_extension_raises():
    with pytest.raises(UnsupportedFileTypeError):
        get_profile("data.json")


def test_get_profile_no_extension_raises():
    with pytest.raises(UnsupportedFileTypeError):
        get_profile("Makefile")
