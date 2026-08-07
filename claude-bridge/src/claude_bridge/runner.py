from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import signal
import subprocess as _subprocess
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Optional, Sequence

logger = logging.getLogger("claude_bridge.runner")

ProgressCallback = Callable[[str], Awaitable[None]]


class RunTimeout(Exception):
    pass


class RunCancelled(Exception):
    pass


@dataclass
class RunResult:
    ok: bool
    session_id: str
    final_text: str
    raw_events: list[dict] = field(default_factory=list)


def _tool_progress_label(event: dict) -> Optional[str]:
    """Turn one stream-json 'assistant' event into a short progress string
    ('編集中: foo.py' / '実行中: pytest ...'), or None if it has no tool_use
    block worth surfacing."""
    message = event.get("message") or {}
    for block in message.get("content") or []:
        if block.get("type") != "tool_use":
            continue
        name = block.get("name", "")
        tool_input = block.get("input") or {}
        if name in ("Edit", "Write", "NotebookEdit"):
            path = tool_input.get("file_path") or tool_input.get("notebook_path") or "?"
            return f"編集中: {Path(path).name}"
        if name == "Read":
            path = tool_input.get("file_path") or "?"
            return f"読み込み中: {Path(path).name}"
        if name == "Bash":
            command = (tool_input.get("command") or "").strip().splitlines()[0][:60]
            return f"実行中: {command}"
        return f"ツール使用: {name}"
    return None


async def _kill_process_tree(process: "asyncio.subprocess.Process") -> None:
    if process.returncode is not None:
        return
    if os.name == "nt":
        killer = await asyncio.create_subprocess_exec(
            "taskkill", "/PID", str(process.pid), "/T", "/F",
            stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        await killer.wait()
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(process.wait(), timeout=5)


async def run_claude(
    instruction: str,
    *,
    project_path: Path,
    session_id: Optional[str],
    is_new_session: bool,
    timeout_seconds: int,
    on_progress: Optional[ProgressCallback] = None,
    progress_interval_seconds: float = 20.0,
    cancel_event: Optional[asyncio.Event] = None,
    claude_command: Sequence[str] = ("claude",),
) -> RunResult:
    """Run `claude -p <instruction>` headlessly in `project_path`, streaming
    tool-use progress to `on_progress` (rate-limited to
    `progress_interval_seconds`), and returning the final result.

    `claude_command` is the argv prefix to run (default `("claude",)`);
    tests point it at a fake stdin-free stand-in (e.g.
    `(sys.executable, "fake_claude.py")`) instead of a real `claude` binary.

    Raises RunTimeout past `timeout_seconds`, or RunCancelled if
    `cancel_event` is set first -- either way the whole process tree is
    force-killed (a plain terminate() wouldn't reach a Bash tool's
    grandchildren).

    Runs with --permission-mode bypassPermissions: there is no TTY here to
    answer a per-tool permission prompt, so leaving permission checks on
    would just hang every run until the timeout killed it. The pre-flight
    keyword guard (guard.py) plus the channel/user/project whitelists are
    the compensating controls -- see the README's Security section.
    """
    new_session_id = session_id or str(uuid.uuid4())
    args = [
        *claude_command, "-p", instruction,
        "--output-format", "stream-json",
        "--verbose",
        "--permission-mode", "bypassPermissions",
    ]
    if session_id and not is_new_session:
        args += ["--resume", session_id]
    else:
        args += ["--session-id", new_session_id]

    spawn_kwargs: dict = {}
    if os.name == "nt":
        spawn_kwargs["creationflags"] = _subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        spawn_kwargs["start_new_session"] = True

    process = await asyncio.create_subprocess_exec(
        *args,
        cwd=str(project_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        **spawn_kwargs,
    )

    raw_events: list[dict] = []
    state = {"final_text": "", "session_id": new_session_id, "ok": False, "last_progress_at": 0.0}

    async def read_stdout() -> None:
        assert process.stdout is not None
        async for raw_line in process.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            raw_events.append(event)

            event_session_id = event.get("session_id")
            if event_session_id:
                state["session_id"] = event_session_id

            if event.get("type") == "result":
                state["final_text"] = event.get("result", "") or ""
                state["ok"] = not event.get("is_error", False)
                continue

            if event.get("type") == "assistant" and on_progress is not None:
                label = _tool_progress_label(event)
                now = time.monotonic()
                if label and now - state["last_progress_at"] >= progress_interval_seconds:
                    state["last_progress_at"] = now
                    await on_progress(label)

    async def watch_cancel() -> None:
        if cancel_event is None:
            # Never resolves; gets cancelled alongside the other task once
            # read_stdout() finishes (or the timeout fires).
            await asyncio.get_running_loop().create_future()
        else:
            await cancel_event.wait()

    stdout_task = asyncio.create_task(read_stdout())
    cancel_task = asyncio.create_task(watch_cancel())

    done, _pending = await asyncio.wait(
        {stdout_task, cancel_task}, timeout=timeout_seconds, return_when=asyncio.FIRST_COMPLETED
    )

    if cancel_task in done:
        await _kill_process_tree(process)
        stdout_task.cancel()
        cancel_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stdout_task
        raise RunCancelled()

    if stdout_task not in done:
        await _kill_process_tree(process)
        stdout_task.cancel()
        cancel_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stdout_task
        raise RunTimeout()

    cancel_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await cancel_task
    await process.wait()

    return RunResult(
        ok=state["ok"], session_id=state["session_id"], final_text=state["final_text"], raw_events=raw_events
    )
