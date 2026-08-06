from pathlib import Path

import pytest

from notesearch.editor import build_editor_command


def test_build_editor_command_default_template():
    result = build_editor_command("code -g {path}:{line}", Path(r"C:\notes\a.md"), 42)
    assert result == ["code", "-g", r"C:\notes\a.md:42"]


def test_build_editor_command_windows_path_not_mangled():
    # A shlex-based implementation (POSIX mode) would treat backslashes
    # as escape characters and corrupt this path; build_editor_command
    # deliberately avoids shlex for exactly this reason.
    result = build_editor_command("code -g {path}:{line}", Path(r"C:\Users\me\notes\deep\file.md"), 1)
    assert result[-1] == r"C:\Users\me\notes\deep\file.md:1"


def test_build_editor_command_custom_template():
    result = build_editor_command("vim +{line} {path}", Path("a.md"), 10)
    assert result == ["vim", "+10", "a.md"]


def test_build_editor_command_empty_template_raises():
    with pytest.raises(ValueError):
        build_editor_command("", Path("a.md"), 1)
