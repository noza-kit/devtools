from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

MAX_MESSAGE_LENGTH = 2000
# ```diff\n ... \n``` fence overhead per chunk.
_FENCE_OVERHEAD = 10
# Beyond this many 2000-char chunks, attach the full diff as a file instead
# of flooding the channel with back-to-back messages.
_MAX_INLINE_CHUNKS = 3


class DiffError(Exception):
    pass


def capture_diff(project_path: Path) -> str:
    """`git diff HEAD` (working tree + staged changes) for the repo at
    `project_path`. Empty string if there's nothing to show -- including the
    not-a-git-repo / no-commits-yet cases, since neither is fatal here."""
    try:
        result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise DiffError(f"failed to run git diff in {project_path}: {exc}") from exc
    if result.returncode != 0:
        return ""
    return result.stdout


def changed_files(project_path: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "HEAD", "--name-only"],
        cwd=project_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line]


@dataclass
class DiffPresentation:
    messages: list[str]  # chunked ```diff``` blocks to post inline
    attachment: Optional[bytes]  # full diff to attach as a file, if too large
    attachment_name: Optional[str]


def render_diff(diff_text: str, *, max_length: int = MAX_MESSAGE_LENGTH) -> DiffPresentation:
    """Split a `git diff` into Discord messages within `max_length` (default
    2000 chars), or -- past `_MAX_INLINE_CHUNKS` -- attach the whole thing as
    a file instead."""
    if not diff_text.strip():
        return DiffPresentation(messages=["変更はありませんでした。"], attachment=None, attachment_name=None)

    budget = max_length - _FENCE_OVERHEAD
    chunks: list[str] = []
    current = ""
    for line in diff_text.splitlines(keepends=True):
        if current and len(current) + len(line) > budget:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)

    if len(chunks) > _MAX_INLINE_CHUNKS:
        line_count = len(diff_text.splitlines())
        return DiffPresentation(
            messages=[f"変更が大きいため diff をファイルで添付します({line_count}行)。"],
            attachment=diff_text.encode("utf-8"),
            attachment_name="changes.diff",
        )

    return DiffPresentation(
        messages=[f"```diff\n{chunk}```" for chunk in chunks],
        attachment=None,
        attachment_name=None,
    )


def render_summary(changed: list[str], claude_summary: Optional[str]) -> str:
    """Build the `mode: summary` text: no diff, just what changed."""
    lines: list[str] = []
    if claude_summary:
        lines.append(claude_summary.strip())
    if changed:
        if lines:
            lines.append("")
        lines.append(f"変更ファイル ({len(changed)}件):")
        lines.extend(f"- {f}" for f in changed)
    return "\n".join(lines) if lines else "変更はありませんでした。"
