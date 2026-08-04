from __future__ import annotations

from pathlib import Path
from typing import List

import typer

from devtoolbox.common.paths import todo_db_path
from devtoolbox.todo.db import (
    TaskNotFoundError,
    add_task,
    get_connection,
    list_tasks,
    remove_task,
    set_done,
)

app = typer.Typer(help="Personal task list", add_completion=True)


def _parse_tags(tags: str) -> list[str]:
    return [t.strip() for t in tags.split(",") if t.strip()]


def _format_line(task) -> str:
    mark = "x" if task.done else " "
    tag_str = f" [{', '.join(task.tags)}]" if task.tags else ""
    return f"[{mark}] #{task.id} {task.text}{tag_str}"


def format_markdown(tasks) -> str:
    lines = ["# TODO", ""]
    if not tasks:
        lines.append("_No tasks._")
    for task in tasks:
        mark = "x" if task.done else " "
        tag_str = f" `{', '.join(task.tags)}`" if task.tags else ""
        lines.append(f"- [{mark}] {task.text}{tag_str}")
    return "\n".join(lines) + "\n"


@app.command()
def add(
    text: str = typer.Argument(..., help="Task description"),
    tags: str = typer.Option("", "--tags", "-t", help="Comma separated tags"),
) -> None:
    """Add a new task."""
    conn = get_connection(todo_db_path())
    try:
        task_id = add_task(conn, text, _parse_tags(tags))
    finally:
        conn.close()

    typer.secho(f"Added task #{task_id}", fg=typer.colors.GREEN)


@app.command(name="list")
def list_cmd(
    tag: List[str] = typer.Option(
        [], "--tag", "-t", help="Filter by tag (repeatable; a task must have all given tags)"
    ),
    all_: bool = typer.Option(False, "--all", "-a", help="Include completed tasks"),
) -> None:
    """List tasks (pending by default)."""
    conn = get_connection(todo_db_path())
    try:
        tasks = list_tasks(conn, tags=tag or None, include_done=all_)
    finally:
        conn.close()

    if not tasks:
        typer.echo("No tasks found.")
        return

    for task in tasks:
        typer.echo(_format_line(task))


@app.command()
def export(
    output: Path = typer.Option(
        Path("TODO.md"), "--output", "-o", help="Output Markdown file"
    ),
    tag: List[str] = typer.Option(
        [], "--tag", "-t", help="Filter by tag (repeatable; a task must have all given tags)"
    ),
    pending_only: bool = typer.Option(
        False, "--pending-only", help="Exclude completed tasks (default: include everything)"
    ),
) -> None:
    """Export tasks as a Markdown checklist (TODO.md by default)."""
    conn = get_connection(todo_db_path())
    try:
        tasks = list_tasks(conn, tags=tag or None, include_done=not pending_only)
    finally:
        conn.close()

    output.write_text(format_markdown(tasks), encoding="utf-8")
    typer.secho(f"Exported {len(tasks)} task(s) to {output}", fg=typer.colors.GREEN)


@app.command()
def done(task_id: int = typer.Argument(..., help="Task id")) -> None:
    """Mark a task as done."""
    conn = get_connection(todo_db_path())
    try:
        set_done(conn, task_id, True)
    except TaskNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        conn.close()

    typer.secho(f"Marked #{task_id} done", fg=typer.colors.GREEN)


@app.command()
def undone(task_id: int = typer.Argument(..., help="Task id")) -> None:
    """Mark a task as not done."""
    conn = get_connection(todo_db_path())
    try:
        set_done(conn, task_id, False)
    except TaskNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        conn.close()

    typer.secho(f"Marked #{task_id} not done", fg=typer.colors.GREEN)


@app.command()
def rm(task_id: int = typer.Argument(..., help="Task id")) -> None:
    """Delete a task."""
    conn = get_connection(todo_db_path())
    try:
        remove_task(conn, task_id)
    except TaskNotFoundError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1)
    finally:
        conn.close()

    typer.secho(f"Removed #{task_id}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
