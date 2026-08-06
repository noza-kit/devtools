import sys
from pathlib import Path

from airshare.watch_hooks import run_hook, run_hooks_for_file


def test_run_hook_success(tmp_path: Path):
    target = tmp_path / "file.md"
    target.write_text("x", encoding="utf-8")
    marker = tmp_path / "marker.txt"
    template = f'{sys.executable} -c "open(r\'{marker}\', \'w\').write(\'ran\')" {{filepath}}'
    assert run_hook(template, target) is True
    assert marker.read_text(encoding="utf-8") == "ran"


def test_run_hook_nonzero_exit_returns_false(tmp_path: Path):
    target = tmp_path / "file.md"
    template = f'{sys.executable} -c "import sys; sys.exit(1)" {{filepath}}'
    assert run_hook(template, target) is False


def test_run_hook_bad_command_does_not_raise(tmp_path: Path):
    target = tmp_path / "file.md"
    assert run_hook("this-command-does-not-exist-xyz {filepath}", target) is False


def test_run_hook_substitutes_windows_path_correctly(tmp_path: Path):
    # A shlex-based (POSIX-mode) implementation would mangle a Windows
    # backslash path; run_hook uses shell=True specifically to avoid that.
    target = tmp_path / "sub" / "file with spaces.md"
    target.parent.mkdir()
    target.write_text("x", encoding="utf-8")
    marker = tmp_path / "seen_path.txt"
    template = f'{sys.executable} -c "import sys; open(r\'{marker}\', \'w\', encoding=\'utf-8\').write(sys.argv[1])" "{{filepath}}"'
    assert run_hook(template, target) is True
    assert marker.read_text(encoding="utf-8") == str(target)


def test_run_hooks_for_file_no_matching_extension_returns_none(tmp_path: Path):
    assert run_hooks_for_file({".pdf": "echo {filepath}"}, tmp_path / "note.md") is None


def test_run_hooks_for_file_matching_extension_runs_it(tmp_path: Path):
    marker = tmp_path / "marker.txt"
    hooks = {".md": f'{sys.executable} -c "open(r\'{marker}\', \'w\').write(\'x\')" {{filepath}}'}
    result = run_hooks_for_file(hooks, tmp_path / "note.md")
    assert result is True
    assert marker.exists()


def test_run_hooks_for_file_extension_matching_case_insensitive(tmp_path: Path):
    marker = tmp_path / "marker.txt"
    hooks = {".md": f'{sys.executable} -c "open(r\'{marker}\', \'w\').write(\'x\')" {{filepath}}'}
    result = run_hooks_for_file(hooks, tmp_path / "NOTE.MD")
    assert result is True
