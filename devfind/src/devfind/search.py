from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

NAME = "NAME"
CONTENT = "CONTENT"


@dataclass(frozen=True)
class Match:
    label: str  # NAME or CONTENT
    path: str


def build_fd_command(keyword: str, target_dirs: Sequence[Path], exclude: Sequence[str]) -> list[str]:
    cmd = ["fd", "--type", "f", "--color", "never"]
    for pattern in exclude:
        cmd += ["--exclude", pattern]
    cmd.append(keyword)
    cmd += [str(d) for d in target_dirs]
    return cmd


def build_rg_command(keyword: str, target_dirs: Sequence[Path], exclude: Sequence[str]) -> list[str]:
    cmd = ["rg", "--files-with-matches", "--color", "never"]
    for pattern in exclude:
        cmd += ["--glob", f"!{pattern}"]
    cmd.append(keyword)
    cmd += [str(d) for d in target_dirs]
    return cmd


def run_fd(keyword: str, target_dirs: Sequence[Path], exclude: Sequence[str]) -> list[str]:
    """`fd` でファイル名検索を実行し、ヒットしたパスの一覧を返す。

    見つからない場合や target_dirs の一部が存在しない場合でも `fd` は非0を
    返すことがあるが、stdout が空ならそのまま空リストになるので exit code
    は見ずに stdout のみを見る。
    """
    cmd = build_fd_command(keyword, target_dirs, exclude)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return _split_lines(result.stdout)


def run_rg(keyword: str, target_dirs: Sequence[Path], exclude: Sequence[str]) -> list[str]:
    """`rg --files-with-matches` で内容一致検索を実行し、ヒットしたパスの一覧を返す。

    `rg` はマッチ0件のとき exit code 1 を返すが、それは失敗ではないので
    `run_fd` 同様 exit code は見ずに stdout のみを見る。
    """
    cmd = build_rg_command(keyword, target_dirs, exclude)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return _split_lines(result.stdout)


def merge_results(fd_paths: Sequence[str], rg_paths: Sequence[str]) -> list[Match]:
    """fdの結果を「ファイル名一致」、rgの結果のうちfdと重複しないものを
    「内容一致」として、ファイル名一致を先頭にしたリストを返す。
    """
    seen: set[str] = set()
    matches: list[Match] = []

    for path in fd_paths:
        key = _normalize(path)
        if key in seen:
            continue
        seen.add(key)
        matches.append(Match(NAME, path))

    for path in rg_paths:
        key = _normalize(path)
        if key in seen:
            continue
        seen.add(key)
        matches.append(Match(CONTENT, path))

    return matches


def _normalize(path: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def _split_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip()]
