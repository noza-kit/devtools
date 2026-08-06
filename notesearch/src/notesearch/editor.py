from __future__ import annotations

import subprocess
from pathlib import Path


def build_editor_command(template: str, path: Path, line: int) -> list[str]:
    """Split `template` on whitespace into argv tokens, then run
    `.format(path=..., line=...)` on each token individually -- a token
    with no `{path}`/`{line}` placeholder (e.g. "code", "-g") passes
    through unchanged, so this handles both a single combined
    "{path}:{line}" argument (VS Code's `code -g path:line`
    convention) and placeholders split across separate arguments (e.g.
    "vim +{line} {path}") the same way. Deliberately not using shlex:
    shlex.split's default POSIX mode treats backslashes as escapes,
    which would corrupt Windows paths -- but a plain whitespace split
    on the template string itself is safe, since backslashes only ever
    appear in the *substituted* path value, never in the template's
    own literal tokens."""
    parts = template.split()
    if not parts:
        raise ValueError("empty editor_command template")
    return [p.format(path=str(path), line=line) for p in parts]


def open_in_editor(template: str, path: Path, line: int = 1) -> None:
    subprocess.Popen(build_editor_command(template, path, line))
