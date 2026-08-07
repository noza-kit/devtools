from __future__ import annotations

import asyncio

import pytest

from claude_bridge.queue_worker import BridgeTask, TaskQueue


def _task(instruction="do it", alias="hobby"):
    return BridgeTask(user_id="1", channel_message_id="1", project_alias=alias, instruction=instruction, mode="diff")


@pytest.mark.asyncio
async def test_tasks_run_one_at_a_time_in_order():
    order: list[str] = []
    started = asyncio.Event()

    async def handler(task: BridgeTask, cancel_event: asyncio.Event) -> None:
        order.append(f"start:{task.instruction}")
        started.set()
        await asyncio.sleep(0.01)
        order.append(f"end:{task.instruction}")

    queue = TaskQueue(handler)
    queue.start()
    await queue.enqueue(_task("first"))
    await queue.enqueue(_task("second"))

    await asyncio.sleep(0.1)
    assert order == ["start:first", "end:first", "start:second", "end:second"]


@pytest.mark.asyncio
async def test_current_and_pending_count_reflect_queue_state():
    release = asyncio.Event()

    async def handler(task: BridgeTask, cancel_event: asyncio.Event) -> None:
        await release.wait()

    queue = TaskQueue(handler)
    queue.start()
    await queue.enqueue(_task("first"))
    await asyncio.sleep(0.01)  # let the worker pick it up
    await queue.enqueue(_task("second"))

    assert queue.current.instruction == "first"
    assert queue.pending_count == 1

    release.set()
    await asyncio.sleep(0.05)
    assert queue.current is None


@pytest.mark.asyncio
async def test_cancel_current_sets_the_running_tasks_event():
    seen_cancel = asyncio.Event()

    async def handler(task: BridgeTask, cancel_event: asyncio.Event) -> None:
        await cancel_event.wait()
        seen_cancel.set()

    queue = TaskQueue(handler)
    queue.start()
    await queue.enqueue(_task())
    await asyncio.sleep(0.01)

    assert queue.cancel_current() is True
    await asyncio.sleep(0.05)
    assert seen_cancel.is_set()


def test_cancel_current_with_nothing_running_returns_false():
    async def handler(task, cancel_event):
        pass

    queue = TaskQueue(handler)
    assert queue.cancel_current() is False
