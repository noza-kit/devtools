from __future__ import annotations

import subprocess
import sys
from typing import Optional, Sequence

from devfind.search import Match
from devfind.tools import is_bat_available

PREVIEW_PLACEHOLDER = "{2..}"


def format_line(match: Match) -> str:
    return f"[{match.label}] {match.path}"


def strip_label(line: str) -> str:
    """`"[NAME] path/to/file"` から先頭のラベルを除いた実パスを返す。"""
    if line.startswith("[") and "] " in line:
        return line.split("] ", 1)[1]
    return line


def build_preview_command() -> str:
    """選択中の行(`[LABEL] path`)からラベルを除いた部分をプレビューするコマンドを返す。

    `bat` があれば使用し、無ければ `cat`(Windowsでは `type`)にフォールバックする。
    """
    if is_bat_available():
        return f"bat --style=numbers --color=always --line-range=:200 {PREVIEW_PLACEHOLDER}"
    if sys.platform == "win32":
        return f"type {PREVIEW_PLACEHOLDER}"
    return f"cat {PREVIEW_PLACEHOLDER}"


def build_fzf_command() -> list[str]:
    return [
        "fzf",
        "--no-sort",
        "--delimiter",
        " ",
        "--preview",
        build_preview_command(),
        "--preview-window",
        "right:60%:wrap",
    ]


def run_fzf(matches: Sequence[Match]) -> Optional[str]:
    """matches を `fzf` に渡し、選択された実パス(ラベル除去済み)を返す。

    matches が空、またはユーザーが選択せずキャンセルした場合は None を返す。
    """
    if not matches:
        return None

    input_text = "\n".join(format_line(m) for m in matches)
    result = subprocess.run(build_fzf_command(), input=input_text, capture_output=True, text=True)

    selected = result.stdout.strip()
    if not selected:
        return None

    return strip_label(selected)
