from __future__ import annotations

import asyncio
import sys
import textwrap

import pytest

from claude_bridge import runner

SUCCESS_SCRIPT = textwrap.dedent(
    """
    import json, sys, time

    args = sys.argv[1:]
    def flag(name):
        return args[args.index(name) + 1] if name in args else None

    session_id = flag("--resume") or flag("--session-id")

    print(json.dumps({
        "type": "assistant", "session_id": session_id,
        "message": {"content": [{"type": "tool_use", "name": "Edit", "input": {"file_path": "foo.py"}}]},
    }), flush=True)
    time.sleep(0.05)
    print(json.dumps({
        "type": "assistant", "session_id": session_id,
        "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "pytest -q"}}]},
    }), flush=True)
    time.sleep(0.05)
    print(json.dumps({
        "type": "result", "session_id": session_id, "result": "Done!", "is_error": False,
    }), flush=True)
    """
)

FAILURE_SCRIPT = textwrap.dedent(
    """
    import json
    print(json.dumps({"type": "result", "session_id": "sess-1", "result": "oops", "is_error": True}), flush=True)
    """
)

HANG_SCRIPT = textwrap.dedent(
    """
    import time
    time.sleep(60)
    """
)


def _write_script(tmp_path, name, body):
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return (sys.executable, str(path))


@pytest.mark.asyncio
async def test_run_claude_success_returns_final_text_and_session_id(tmp_path):
    command = _write_script(tmp_path, "fake_claude_success.py", SUCCESS_SCRIPT)

    progress_labels = []

    async def on_progress(label: str) -> None:
        progress_labels.append(label)

    result = await runner.run_claude(
        "do something",
        project_path=tmp_path,
        session_id=None,
        is_new_session=True,
        timeout_seconds=10,
        on_progress=on_progress,
        progress_interval_seconds=0,
        claude_command=command,
    )

    assert result.ok is True
    assert result.final_text == "Done!"
    assert progress_labels == ["編集中: foo.py", "実行中: pytest -q"]


@pytest.mark.asyncio
async def test_run_claude_passes_session_id_via_resume(tmp_path):
    command = _write_script(tmp_path, "fake_claude_success.py", SUCCESS_SCRIPT)

    result = await runner.run_claude(
        "follow up",
        project_path=tmp_path,
        session_id="existing-session",
        is_new_session=False,
        timeout_seconds=10,
        claude_command=command,
    )

    assert result.session_id == "existing-session"


@pytest.mark.asyncio
async def test_run_claude_progress_is_rate_limited(tmp_path):
    command = _write_script(tmp_path, "fake_claude_success.py", SUCCESS_SCRIPT)

    progress_labels = []

    async def on_progress(label: str) -> None:
        progress_labels.append(label)

    await runner.run_claude(
        "do something",
        project_path=tmp_path,
        session_id=None,
        is_new_session=True,
        timeout_seconds=10,
        on_progress=on_progress,
        progress_interval_seconds=999,  # effectively never re-fire after the first
        claude_command=command,
    )

    assert progress_labels == ["編集中: foo.py"]


@pytest.mark.asyncio
async def test_run_claude_error_result_marks_not_ok(tmp_path):
    command = _write_script(tmp_path, "fake_claude_failure.py", FAILURE_SCRIPT)

    result = await runner.run_claude(
        "do something",
        project_path=tmp_path,
        session_id=None,
        is_new_session=True,
        timeout_seconds=10,
        claude_command=command,
    )

    assert result.ok is False
    assert result.final_text == "oops"


@pytest.mark.asyncio
async def test_run_claude_timeout_raises_and_kills_process(tmp_path):
    command = _write_script(tmp_path, "fake_claude_hang.py", HANG_SCRIPT)

    with pytest.raises(runner.RunTimeout):
        await runner.run_claude(
            "do something",
            project_path=tmp_path,
            session_id=None,
            is_new_session=True,
            timeout_seconds=0.2,
            claude_command=command,
        )


@pytest.mark.asyncio
async def test_run_claude_cancel_event_raises_run_cancelled(tmp_path):
    command = _write_script(tmp_path, "fake_claude_hang.py", HANG_SCRIPT)
    cancel_event = asyncio.Event()

    async def cancel_soon():
        await asyncio.sleep(0.1)
        cancel_event.set()

    asyncio.create_task(cancel_soon())

    with pytest.raises(runner.RunCancelled):
        await runner.run_claude(
            "do something",
            project_path=tmp_path,
            session_id=None,
            is_new_session=True,
            timeout_seconds=10,
            cancel_event=cancel_event,
            claude_command=command,
        )
