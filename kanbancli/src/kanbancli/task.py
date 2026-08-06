from __future__ import annotations

import random
import re
import string
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

# Roman-numeral progress tokens i..ix = 10%..90%, chosen (per project decision)
# because "x" already means 10 in Roman numerals and is exactly the symbol used
# for "complete" -- [i]..[ix] extend that same numbering down to partial progress.
_ROMAN_PROGRESS = {"i": 10, "ii": 20, "iii": 30, "iv": 40, "v": 50, "vi": 60, "vii": 70, "viii": 80, "ix": 90}

# status token -> (category, percent-or-None)
STATUS_TOKENS: dict[str, tuple[str, Optional[int]]] = {
    " ": ("todo", None),
    "": ("todo", None),
    "~": ("in_progress", None),
    "/": ("in_progress", None),
    "x": ("done", 100),
    "-": ("cancelled", None),
    ">": ("postponed", None),
    **{tok: ("progress", pct) for tok, pct in _ROMAN_PROGRESS.items()},
}

# Friendly aliases accepted by `kanbancli update`, in addition to raw tokens.
STATUS_ALIASES: dict[str, str] = {
    "todo": " ",
    "start": "~",
    "doing": "~",
    "done": "x",
    "complete": "x",
    "cancel": "-",
    "cancelled": "-",
    "postpone": ">",
    "postponed": ">",
    **{str(pct): tok for tok, pct in _ROMAN_PROGRESS.items()},
}

PRIORITY_MARKERS = ("", "!", "!!", "!!!")

_ID_ALPHABET = string.ascii_lowercase + string.digits
_ID_LENGTH = 4

_LINE_RE = re.compile(r"^(?P<indent>[ \t]*)-\s*\[(?P<status>[^\]]*)\]\s*(?P<rest>.*)$")
_PRIORITY_RE = re.compile(r"\[(!{1,3})\]")
_ADD_RE = re.compile(r"@add:(\d{4}-\d{2}-\d{2})")
_DUE_RE = re.compile(r"@due:(\d{4}-\d{2}-\d{2})")
_RECUR_RE = re.compile(r"@recur:(\S+)")
_DEPENDS_RE = re.compile(r"@depends:([A-Za-z0-9]+)")
_TAG_RE = re.compile(r"#(\S+)")
_ID_RE = re.compile(r"\bid:([A-Za-z0-9]+)\b")


class TaskParseError(ValueError):
    pass


@dataclass
class Task:
    id: str
    content: str
    status_token: str = " "
    priority: int = 0  # 0-3, number of "!"
    add_date: Optional[date] = None
    due_date: Optional[date] = None
    recur: Optional[str] = None
    depends: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    level: int = 0  # indent depth; 0 = top-level task

    @property
    def category(self) -> str:
        return STATUS_TOKENS.get(self.status_token, ("todo", None))[0]

    @property
    def percent(self) -> Optional[int]:
        return STATUS_TOKENS.get(self.status_token, ("todo", None))[1]

    @property
    def is_done(self) -> bool:
        return self.category == "done"

    @property
    def is_terminal(self) -> bool:
        """Done or cancelled -- what `archive` sweeps up."""
        return self.category in ("done", "cancelled")


def generate_id(existing_ids: set[str]) -> str:
    """A 4-char lowercase-alphanumeric id, regenerated on collision
    (collisions are rare enough at this scale that a bounded retry loop
    is simpler and plenty reliable vs. any smarter scheme)."""
    for _ in range(1000):
        candidate = "".join(random.choices(_ID_ALPHABET, k=_ID_LENGTH))
        if candidate not in existing_ids:
            return candidate
    raise RuntimeError("could not generate a unique task id after 1000 attempts")


def resolve_status_token(value: str) -> str:
    """Accept either a raw bracket token (" ", "~", "i".."ix", "x", "-",
    ">") or a friendly alias ("done", "start", "30", ...); raises
    TaskParseError for anything else."""
    if value in STATUS_TOKENS:
        return value
    if value in STATUS_ALIASES:
        return STATUS_ALIASES[value]
    raise TaskParseError(
        f"unknown status '{value}' (expected one of {sorted(STATUS_TOKENS)} or an alias like "
        f"{sorted(STATUS_ALIASES)})"
    )


def parse_line(line: str) -> Optional[Task]:
    """Parse one Markdown task line into a Task, or None if the line
    isn't a task line at all (blank lines, prose, etc. are simply
    skipped by the caller)."""
    m = _LINE_RE.match(line)
    if not m:
        return None

    indent = m.group("indent").expandtabs(4)
    level = len(indent) // 2  # 2 or 4 spaces per level both resolve cleanly to level via //2 on tab-expanded indent
    status_token = m.group("status")
    rest = m.group("rest")

    id_match = _ID_RE.search(rest)
    if not id_match:
        raise TaskParseError(f"task line has no id:XXXX: {line!r}")
    task_id = id_match.group(1)
    rest = _ID_RE.sub("", rest)

    priority_match = _PRIORITY_RE.search(rest)
    priority = len(priority_match.group(1)) if priority_match else 0
    rest = _PRIORITY_RE.sub("", rest)

    add_match = _ADD_RE.search(rest)
    add_date = date.fromisoformat(add_match.group(1)) if add_match else None
    rest = _ADD_RE.sub("", rest)

    due_match = _DUE_RE.search(rest)
    due_date = date.fromisoformat(due_match.group(1)) if due_match else None
    rest = _DUE_RE.sub("", rest)

    recur_match = _RECUR_RE.search(rest)
    recur = recur_match.group(1) if recur_match else None
    rest = _RECUR_RE.sub("", rest)

    depends = _DEPENDS_RE.findall(rest)
    rest = _DEPENDS_RE.sub("", rest)

    tags = _TAG_RE.findall(rest)
    rest = _TAG_RE.sub("", rest)

    content = re.sub(r"\s+", " ", rest).strip()

    return Task(
        id=task_id,
        content=content,
        status_token=status_token,
        priority=priority,
        add_date=add_date,
        due_date=due_date,
        recur=recur,
        depends=depends,
        tags=tags,
        level=level,
    )


def format_line(task: Task) -> str:
    """Inverse of parse_line: render a Task back to its Markdown line,
    in the canonical attribute order (priority, @add, @due, @recur,
    @depends..., #tags..., id: last)."""
    parts = [f"{'  ' * task.level}- [{task.status_token}] {task.content}"]
    if task.priority:
        parts.append(f"[{'!' * task.priority}]")
    if task.add_date:
        parts.append(f"@add:{task.add_date.isoformat()}")
    if task.due_date:
        parts.append(f"@due:{task.due_date.isoformat()}")
    if task.recur:
        parts.append(f"@recur:{task.recur}")
    for dep in task.depends:
        parts.append(f"@depends:{dep}")
    for tag in task.tags:
        parts.append(f"#{tag}")
    parts.append(f"id:{task.id}")
    return " ".join(parts)
