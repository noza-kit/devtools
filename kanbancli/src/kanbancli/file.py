from __future__ import annotations

from pathlib import Path
from typing import Optional

from kanbancli.task import Task, TaskParseError, format_line, parse_line

LOCAL_FILENAME = ".kanban.md"
GLOBAL_PATH = Path.home() / ".config" / "kanbancli" / "tasks.md"


def resolve_task_file(explicit: Optional[Path] = None, start_dir: Optional[Path] = None) -> Path:
    """Hybrid file resolution: an explicit `--file` always wins; else
    look for `.kanban.md` in `start_dir` (default: cwd) and its
    parents; else fall back to the global `~/.config/kanbancli/tasks.md`
    (which may not exist yet -- callers create it on first write, same
    as devfind's config resolution)."""
    if explicit is not None:
        return explicit

    here = start_dir or Path.cwd()
    for candidate_dir in (here, *here.parents):
        candidate = candidate_dir / LOCAL_FILENAME
        if candidate.exists():
            return candidate

    return GLOBAL_PATH


def load_tasks(path: Path) -> list[Task]:
    """Parse a task file into a flat list of Task (subtasks are
    represented by `Task.level`, not nesting, so filtering/dependency
    logic doesn't need to walk a tree). A missing file is treated as an
    empty task list (first-run friendly), not an error."""
    if not path.exists():
        return []

    tasks: list[Task] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            task = parse_line(line)
        except TaskParseError as e:
            raise TaskParseError(f"{path}:{lineno}: {e}") from e
        if task is not None:
            tasks.append(task)
    return tasks


def save_tasks(path: Path, tasks: list[Task]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [format_line(t) for t in tasks]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def find_task(tasks: list[Task], task_id: str) -> Optional[Task]:
    return next((t for t in tasks if t.id == task_id), None)


def existing_ids(tasks: list[Task]) -> set[str]:
    return {t.id for t in tasks}
