from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from kanbancli import ops
from kanbancli.autostart import AutostartError, register_autostart, remove_autostart
from kanbancli.file import load_tasks, resolve_task_file, save_tasks
from kanbancli.recur import RecurError, parse_recur_spec
from kanbancli.remind import send_reminder
from kanbancli.task import Task, TaskParseError

app = typer.Typer(help="Offline, Markdown-file-backed kanban CLI.")
console = Console()
err_console = Console(stderr=True)


def _fail(message: str) -> None:
    err_console.print(f"[red]エラー: {message}[/red]")
    raise typer.Exit(code=1)


def _load(file: Optional[Path]) -> tuple[Path, list[Task]]:
    path = resolve_task_file(file)
    try:
        return path, load_tasks(path)
    except TaskParseError as e:
        _fail(str(e))


def _parse_date(value: Optional[str]) -> Optional[date]:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        _fail(f"日付は YYYY-MM-DD 形式で指定してください: {value!r}")


def _parse_priority(value: Optional[str]) -> int:
    if value is None:
        return 0
    if value not in ("!", "!!", "!!!"):
        _fail("--priority は !, !!, !!! のいずれかで指定してください")
    return len(value)


def _print_tasks(tasks: list[Task]) -> None:
    table = Table("id", "status", "pri", "content", "due", "tags")
    for t in tasks:
        status_display = f"[{t.status_token}] {t.percent}%" if t.percent is not None else f"[{t.status_token}]"
        indent = "  " * t.level
        table.add_row(
            t.id,
            status_display,
            "!" * t.priority,
            f"{indent}{t.content}",
            t.due_date.isoformat() if t.due_date else "",
            ",".join(t.tags),
        )
    console.print(table)


@app.command()
def add(
    content: Optional[str] = typer.Argument(None),
    due: Optional[str] = typer.Option(None, "--due"),
    priority: Optional[str] = typer.Option(None, "--priority", help="!, !!, or !!!"),
    tags: Optional[str] = typer.Option(None, "--tags", help="comma-separated"),
    depends: Optional[str] = typer.Option(None, "--depends", help="comma-separated task ids"),
    parent: Optional[str] = typer.Option(None, "--parent", help="add as a subtask of this task id"),
    recur: Optional[str] = typer.Option(None, "--recur", help="e.g. 1d, 2w, 1m, 1y"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
) -> None:
    """Add a task. Run with no CONTENT for an interactive prompt."""
    if content is None:
        content = typer.prompt("タスク内容")
        due = typer.prompt("期限 (YYYY-MM-DD, 空欄可)", default="", show_default=False) or None
        priority = typer.prompt("優先度 (!, !!, !!!, 空欄可)", default="", show_default=False) or None
        tags = typer.prompt("タグ (カンマ区切り, 空欄可)", default="", show_default=False) or None

    path, tasks = _load(file)
    try:
        new_task = ops.add_task(
            tasks,
            content=content,
            priority=_parse_priority(priority),
            due=_parse_date(due),
            tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else None,
            depends=[d.strip() for d in depends.split(",") if d.strip()] if depends else None,
            parent_id=parent,
        )
        if recur:
            parse_recur_spec(recur)  # validate now rather than failing later when the task is completed
            new_task.recur = recur
    except (ops.TaskNotFoundError, RecurError) as e:
        _fail(str(e))

    save_tasks(path, tasks)
    console.print(f"[green]追加しました[/green]: id:{new_task.id} {new_task.content}  ({path})")


@app.command()
def update(
    task_id: str,
    status: str,
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
) -> None:
    """Update a task's status. STATUS is a raw token (" ", "~", "i".."ix", "x", "-", ">")
    or a friendly alias (todo/start/done/cancel/postpone/10../90)."""
    path, tasks = _load(file)
    try:
        task, generated = ops.update_status(tasks, task_id, status)
    except (ops.TaskNotFoundError, TaskParseError, RecurError) as e:
        _fail(str(e))

    save_tasks(path, tasks)
    console.print(f"[green]更新しました[/green]: id:{task.id} -> [{task.status_token}] {task.content}")
    if generated:
        console.print(f"[cyan]次回分を生成しました[/cyan]: id:{generated.id} @due:{generated.due_date}")


@app.command("list")
def list_cmd(
    sort: Optional[str] = typer.Option(None, "--sort", help="priority | due"),
    available: bool = typer.Option(False, "--available", help="ブロッカーが無い(未完了かつ@dependsが全て完了済み)タスクのみ"),
    tag: Optional[str] = typer.Option(None, "--tag"),
    status: Optional[str] = typer.Option(None, "--status", help="todo/in_progress/progress/done/cancelled/postponed"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
) -> None:
    """List tasks."""
    _, tasks = _load(file)
    result = ops.list_tasks(tasks, sort_by=sort, available_only=available, tag=tag, status=status)
    if not result:
        console.print("タスクがありません。")
        return
    _print_tasks(result)


@app.command()
def export(
    output: Path,
    tags: Optional[str] = typer.Option(None, "--tags", help="comma-separated; matches any"),
    statuses: Optional[str] = typer.Option(None, "--status", help="comma-separated categories"),
    due_before: Optional[str] = typer.Option(None, "--due-before"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
) -> None:
    """Export a filtered subset of tasks to another Markdown file."""
    _, tasks = _load(file)
    filtered = ops.filter_tasks(
        tasks,
        tags=[t.strip() for t in tags.split(",") if t.strip()] if tags else None,
        statuses=[s.strip() for s in statuses.split(",") if s.strip()] if statuses else None,
        due_before=_parse_date(due_before),
    )
    count = ops.export_tasks(filtered, output)
    console.print(f"[green]{count}件のタスクをエクスポートしました[/green] -> {output}")


@app.command()
def archive(
    archive_path: Optional[Path] = typer.Option(None, "--archive-path"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
) -> None:
    """Move done/cancelled tasks out of the main file into an archive file."""
    path, tasks = _load(file)
    target = archive_path or (path.parent / "archive.md")
    remaining, archived = ops.archive_tasks(tasks, target)
    save_tasks(path, remaining)
    console.print(f"[green]{len(archived)}件のタスクをアーカイブしました[/green] -> {target}")


@app.command()
def remind(
    within_days: int = typer.Option(3, "--within-days"),
    channels: Optional[str] = typer.Option(None, "--channels", help="comma-separated notify channels (default: desktop)"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
) -> None:
    """Check for due-soon/overdue tasks and send one notify() summary if there are any."""
    _, tasks = _load(file)
    result = send_reminder(
        tasks,
        within_days=within_days,
        channels=[c.strip() for c in channels.split(",") if c.strip()] if channels else None,
    )
    if result is None:
        console.print("期限が近いタスクはありません。")
    else:
        console.print("[green]通知を送信しました[/green]")


@app.command("setup-autostart")
def setup_autostart(
    task_name: str = typer.Option("KanbancliRemind", "--task-name"),
    time: str = typer.Option("09:00", "--time", help="HH:MM, 24-hour"),
    within_days: int = typer.Option(3, "--within-days"),
    channels: Optional[str] = typer.Option(None, "--channels"),
    file: Optional[Path] = typer.Option(None, "--file", "-f"),
    remove: bool = typer.Option(False, "--remove"),
) -> None:
    """Register (or --remove) a daily Windows Task Scheduler reminder."""
    try:
        if remove:
            remove_autostart(task_name=task_name)
            console.print(f"[green]タスクを削除しました[/green]: {task_name}")
        else:
            register_autostart(
                task_name=task_name,
                start_time=time,
                within_days=within_days,
                channels=[c.strip() for c in channels.split(",") if c.strip()] if channels else None,
                file=file,
            )
            console.print(f"[green]毎日{time}に実行するタスクを登録しました[/green]: {task_name}")
    except AutostartError as e:
        _fail(str(e))
