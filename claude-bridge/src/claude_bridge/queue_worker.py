from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

logger = logging.getLogger("claude_bridge.queue")


@dataclass
class BridgeTask:
    user_id: str
    channel_message_id: str
    project_alias: str
    instruction: str
    mode: str


TaskHandler = Callable[[BridgeTask, asyncio.Event], Awaitable[None]]


class TaskQueue:
    """Single-worker FIFO queue: only one BridgeTask runs `claude -p` at a
    time (concurrent Claude Code sessions against the same project aren't
    safe), everything else waits. `cancel_current()` sets the cancel event
    the running handler is expected to be awaiting on."""

    def __init__(self, handler: TaskHandler):
        self._queue: "asyncio.Queue[BridgeTask]" = asyncio.Queue()
        self._handler = handler
        self._current: Optional[BridgeTask] = None
        self._current_cancel_event: Optional[asyncio.Event] = None
        self._worker_task: Optional[asyncio.Task] = None

    def start(self) -> None:
        self._worker_task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._worker_task is not None:
            self._worker_task.cancel()

    async def enqueue(self, task: BridgeTask) -> None:
        await self._queue.put(task)

    @property
    def current(self) -> Optional[BridgeTask]:
        return self._current

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    def cancel_current(self) -> bool:
        if self._current_cancel_event is None:
            return False
        self._current_cancel_event.set()
        return True

    async def _run(self) -> None:
        while True:
            task = await self._queue.get()
            self._current = task
            self._current_cancel_event = asyncio.Event()
            try:
                await self._handler(task, self._current_cancel_event)
            except Exception:
                logger.exception("task handler failed for project=%s", task.project_alias)
            finally:
                self._current = None
                self._current_cancel_event = None
                self._queue.task_done()
