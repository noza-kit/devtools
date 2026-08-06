from __future__ import annotations

import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolInfo:
    name: str
    install_hint: str


REQUIRED_TOOLS: dict[str, ToolInfo] = {
    "fd": ToolInfo(
        "fd",
        "winget install sharkdp.fd / choco install fd / scoop install fd / "
        "brew install fd / apt install fd-find",
    ),
    "rg": ToolInfo(
        "rg",
        "winget install BurntSushi.ripgrep.MSVC / choco install ripgrep / "
        "scoop install ripgrep / brew install ripgrep / apt install ripgrep",
    ),
    "fzf": ToolInfo(
        "fzf",
        "winget install junegunn.fzf / choco install fzf / scoop install fzf / "
        "brew install fzf / apt install fzf",
    ),
}

OPTIONAL_TOOLS: dict[str, ToolInfo] = {
    "bat": ToolInfo(
        "bat",
        "winget install sharkdp.bat / choco install bat / scoop install bat / "
        "brew install bat / apt install bat",
    ),
}


class MissingToolError(Exception):
    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__(_format_message(missing))


def _format_message(missing: list[str]) -> str:
    lines = ["devfind の実行に必要なコマンドが見つかりません:", ""]
    for name in missing:
        lines.append(f"  - {name}: {REQUIRED_TOOLS[name].install_hint}")
    lines.append("")
    lines.append("インストール後、PATH が通っていることを確認してから再実行してください。")
    return "\n".join(lines)


def find_missing_required_tools() -> list[str]:
    return [name for name in REQUIRED_TOOLS if shutil.which(name) is None]


def ensure_required_tools() -> None:
    missing = find_missing_required_tools()
    if missing:
        raise MissingToolError(missing)


def is_bat_available() -> bool:
    return shutil.which("bat") is not None
