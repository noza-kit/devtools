from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from notify import notify

from kanbancli.task import Task


def due_soon_tasks(tasks: list[Task], within_days: int = 3, today: Optional[date] = None) -> list[Task]:
    """Open (not done/cancelled) tasks whose @due date is today, already
    overdue, or within `within_days` days from now."""
    today = today or date.today()
    horizon = today + timedelta(days=within_days)
    return [
        t
        for t in tasks
        if t.due_date is not None and t.category not in ("done", "cancelled") and t.due_date <= horizon
    ]


def format_reminder(due_tasks: list[Task], today: Optional[date] = None) -> str:
    today = today or date.today()
    lines = ["[kanbancli] 期限が近い/超過しているタスク:"]
    for t in sorted(due_tasks, key=lambda t: t.due_date):
        marker = " (期限超過)" if t.due_date < today else ""
        lines.append(f"  - {t.content} (@due:{t.due_date.isoformat()}{marker}) id:{t.id}")
    return "\n".join(lines)


def send_reminder(
    tasks: list[Task],
    within_days: int = 3,
    channels: Optional[list[str]] = None,
    config=None,
    today: Optional[date] = None,
) -> Optional[dict]:
    """Sends one notify() call summarizing every due-soon/overdue task,
    or does nothing (returns None) if there's nothing to report."""
    due = due_soon_tasks(tasks, within_days, today)
    if not due:
        return None
    message = format_reminder(due, today)
    return notify(message, channels=channels or ["desktop"], config=config)
