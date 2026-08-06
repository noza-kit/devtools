from __future__ import annotations

import subprocess

from devfind.fzf import build_preview_command, format_line, run_fzf, strip_label
from devfind.search import CONTENT, NAME, Match


def test_format_line_adds_label_prefix():
    assert format_line(Match(NAME, "a/one.txt")) == "[NAME] a/one.txt"
    assert format_line(Match(CONTENT, "a/two.txt")) == "[CONTENT] a/two.txt"


def test_strip_label_removes_prefix():
    assert strip_label("[NAME] a/one.txt") == "a/one.txt"
    assert strip_label("[CONTENT] a/two.txt") == "a/two.txt"


def test_strip_label_preserves_paths_containing_bracket_sequence():
    # A path itself containing "] " right after the label is reconstructed
    # verbatim by only splitting on the first occurrence.
    assert strip_label("[NAME] weird] name.txt") == "weird] name.txt"


def test_strip_label_returns_input_unchanged_when_no_label():
    assert strip_label("a/one.txt") == "a/one.txt"


def test_build_preview_command_uses_bat_when_available(monkeypatch):
    monkeypatch.setattr("devfind.fzf.is_bat_available", lambda: True)

    cmd = build_preview_command()

    assert cmd.startswith("bat ")
    assert "{2..}" in cmd


def test_build_preview_command_falls_back_to_cat_on_non_windows(monkeypatch):
    monkeypatch.setattr("devfind.fzf.is_bat_available", lambda: False)
    monkeypatch.setattr("devfind.fzf.sys.platform", "linux")

    assert build_preview_command() == "cat {2..}"


def test_build_preview_command_falls_back_to_type_on_windows(monkeypatch):
    monkeypatch.setattr("devfind.fzf.is_bat_available", lambda: False)
    monkeypatch.setattr("devfind.fzf.sys.platform", "win32")

    assert build_preview_command() == "type {2..}"


def test_run_fzf_returns_none_without_calling_subprocess_when_no_matches(monkeypatch):
    called = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: called.append(1))

    result = run_fzf([])

    assert result is None
    assert called == []


def test_run_fzf_returns_stripped_path_on_selection(monkeypatch):
    class FakeResult:
        stdout = "[CONTENT] a/two.txt\n"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeResult())

    result = run_fzf([Match(NAME, "a/one.txt"), Match(CONTENT, "a/two.txt")])

    assert result == "a/two.txt"


def test_run_fzf_returns_none_when_cancelled(monkeypatch):
    class FakeResult:
        stdout = ""

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: FakeResult())

    result = run_fzf([Match(NAME, "a/one.txt")])

    assert result is None


def test_run_fzf_passes_lines_as_input(monkeypatch):
    captured = {}

    class FakeResult:
        stdout = "[NAME] a/one.txt\n"

    def fake_run(cmd, input=None, **kwargs):
        captured["cmd"] = cmd
        captured["input"] = input
        return FakeResult()

    monkeypatch.setattr(subprocess, "run", fake_run)

    run_fzf([Match(NAME, "a/one.txt"), Match(CONTENT, "a/two.txt")])

    assert captured["cmd"][0] == "fzf"
    assert captured["input"] == "[NAME] a/one.txt\n[CONTENT] a/two.txt"
