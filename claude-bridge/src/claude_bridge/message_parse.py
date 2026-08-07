from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

_PROJECT_RE = re.compile(r"(?im)^[ \t]*project[ \t]*:[ \t]*(\S+)[ \t]*$")
_MODE_RE = re.compile(r"(?im)^[ \t]*mode[ \t]*:[ \t]*(diff|summary)[ \t]*$")


@dataclass(frozen=True)
class ParsedMessage:
    instruction: str
    project_alias: Optional[str]
    mode: Optional[str]


def parse_directives(content: str) -> ParsedMessage:
    """Pull `project: <alias>` / `mode: diff|summary` directive lines out of
    a Discord message (each expected on its own line), returning what's left
    as the actual instruction to hand to `claude -p`."""
    project_match = _PROJECT_RE.search(content)
    mode_match = _MODE_RE.search(content)

    remaining = _PROJECT_RE.sub("", content)
    remaining = _MODE_RE.sub("", remaining)
    instruction = remaining.strip()

    return ParsedMessage(
        instruction=instruction,
        project_alias=project_match.group(1) if project_match else None,
        mode=mode_match.group(1).lower() if mode_match else None,
    )
