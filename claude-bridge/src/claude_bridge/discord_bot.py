from __future__ import annotations

import asyncio
import io
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import discord
from notify import notify

from claude_bridge import diff_view, runner
from claude_bridge.config import Secrets, Settings, find_project
from claude_bridge.history_db import HistoryDB
from claude_bridge.queue_worker import BridgeTask, TaskQueue
from claude_bridge.routing import IncomingMessage, PendingConfirmation, decide
from claude_bridge.runtime_state import RuntimeState, write_runtime_state

logger = logging.getLogger("claude_bridge.bot")

MAX_MESSAGE_LENGTH = 2000
STATUS_WRITE_INTERVAL_SECONDS = 5


class BridgeClient(discord.Client):
    def __init__(self, settings: Settings, secrets: Secrets, history_db: HistoryDB, **kwargs):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents, **kwargs)
        self.settings = settings
        self.secrets = secrets
        self.history_db = history_db
        self._pending: Optional[PendingConfirmation] = None
        self._paused = False
        self._queue = TaskQueue(self._handle_task)
        self._channel: Optional[discord.abc.Messageable] = None
        self._started_at = datetime.now(timezone.utc).isoformat()

    async def setup_hook(self) -> None:
        self._queue.start()
        self.loop.create_task(self._status_loop())
        if self.settings.heartbeat_enabled:
            self.loop.create_task(self._heartbeat_loop())

    async def on_ready(self) -> None:
        self._channel = self.get_channel(int(self.secrets.channel_id))
        logger.info("claude-bridge connected as %s (channel=%s)", self.user, self.secrets.channel_id)
        notify(f"claude-bridge 起動しました ({self.user})", channels=["desktop"])

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        incoming = IncomingMessage(
            author_id=str(message.author.id),
            channel_id=str(message.channel.id),
            message_id=str(message.id),
            content=message.content,
        )
        decision = decide(
            incoming,
            self.settings,
            allowed_channel_id=str(self.secrets.channel_id),
            allowed_user_ids=self.secrets.allowed_user_ids,
            pending=self._pending,
            has_running_task=self._queue.current is not None,
            is_paused=self._paused,
        )

        if decision.kind == "ignore":
            return

        if decision.kind == "notice":
            await message.channel.send(decision.reply)
            return

        if decision.kind == "pause":
            self._paused = True
            self._pending = None
            self._queue.cancel_current()
            await message.channel.send(decision.reply)
            return

        if decision.kind == "resume":
            self._paused = False
            await message.channel.send(decision.reply)
            return

        if decision.kind == "cancel":
            self._queue.cancel_current()
            await message.channel.send("\N{OCTAGONAL SIGN} 実行中のタスクを中断します...")
            return

        if decision.kind == "usage":
            await self._send_usage_report(message.channel)
            return

        if decision.kind in ("unknown_project", "confirmation_declined"):
            self._pending = None
            await message.channel.send(decision.reply)
            return

        if decision.kind == "await_confirmation":
            self._pending = decision.pending
            await message.channel.send(decision.reply)
            notify(f"claude-bridge: 破壊的操作の確認待ちです({decision.reply})", channels=["desktop"])
            return

        assert decision.kind == "run"
        self._pending = None
        task = BridgeTask(
            user_id=incoming.author_id,
            channel_message_id=incoming.message_id,
            project_alias=decision.project_alias,
            instruction=decision.instruction,
            mode=decision.mode,
        )
        await self._queue.enqueue(task)
        queued_note = f"(キュー: {self._queue.pending_count}件待ち)" if self._queue.pending_count else ""
        await message.channel.send(f"\N{INBOX TRAY} 受け付けました: `{task.project_alias}` {queued_note}")

    # -- task execution ------------------------------------------------------

    async def _handle_task(self, task: BridgeTask, cancel_event: asyncio.Event) -> None:
        project = find_project(self.settings, task.project_alias)
        channel = self._channel or self.get_channel(int(self.secrets.channel_id))
        session_id = self.history_db.get_session_id(task.project_alias)
        run_id = self.history_db.start_run(
            project_alias=task.project_alias, user_id=task.user_id, instruction=task.instruction, mode=task.mode
        )

        async def on_progress(label: str) -> None:
            await channel.send(f"\N{HOURGLASS WITH FLOWING SAND} 作業中: {label}")

        try:
            result = await runner.run_claude(
                task.instruction,
                project_path=project.path,
                session_id=session_id,
                is_new_session=session_id is None,
                timeout_seconds=self.settings.timeout_seconds,
                on_progress=on_progress,
                progress_interval_seconds=self.settings.progress_interval_seconds,
                cancel_event=cancel_event,
            )
        except runner.RunTimeout:
            self.history_db.finish_run(run_id, status="timeout", result_summary=None, session_id=session_id)
            minutes = self.settings.timeout_seconds // 60
            await channel.send(f"\N{ALARM CLOCK} タイムアウトしました({minutes}分)。")
            notify(f"claude-bridge: {task.project_alias} がタイムアウトしました", channels=["desktop"])
            return
        except runner.RunCancelled:
            self.history_db.finish_run(run_id, status="cancelled", result_summary=None, session_id=session_id)
            await channel.send("\N{OCTAGONAL SIGN} 中断しました。")
            return
        except Exception as exc:
            logger.exception("claude run failed for project=%s", task.project_alias)
            self.history_db.finish_run(run_id, status="failed", result_summary=str(exc), session_id=session_id)
            await channel.send(f"\N{CROSS MARK} 実行に失敗しました: {exc}")
            notify(f"claude-bridge: {task.project_alias} の実行に失敗しました: {exc}", channels=["desktop"])
            return

        self.history_db.set_session_id(task.project_alias, result.session_id)
        status = "completed" if result.ok else "failed"
        self.history_db.finish_run(
            run_id,
            status=status,
            result_summary=result.final_text[:500],
            session_id=result.session_id,
            total_cost_usd=result.total_cost_usd,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            cache_creation_input_tokens=result.cache_creation_input_tokens,
            cache_read_input_tokens=result.cache_read_input_tokens,
        )

        if result.final_text:
            await self._send_chunked(channel, result.final_text)
        await self._send_diff_or_summary(channel, task, project.path, result.final_text)

        if result.total_cost_usd is not None:
            total = self.history_db.usage_summary().total_cost_usd
            await channel.send(
                f"\N{MONEY BAG} 概算コスト: ${result.total_cost_usd:.4f}(累計: ${total:.4f}。"
                "内訳は `usage` と送信)"
            )

    async def _send_usage_report(self, channel) -> None:
        all_time = self.history_db.usage_summary()
        recent = self.history_db.usage_summary(since_days=7)
        by_project = self.history_db.usage_by_project()

        lines = [
            "\N{BAR CHART} 使用量(概算コスト)",
            f"全期間: {all_time.run_count}回 / ${all_time.total_cost_usd:.4f}",
            f"直近7日間: {recent.run_count}回 / ${recent.total_cost_usd:.4f}",
        ]
        if by_project:
            lines.append("")
            lines.append("プロジェクト別(全期間):")
            lines.extend(f"- {p.project_alias}: {p.run_count}回 / ${p.total_cost_usd:.4f}" for p in by_project)

        await channel.send("\n".join(lines))

    async def _send_diff_or_summary(self, channel, task: BridgeTask, project_path: Path, claude_summary: str) -> None:
        if task.mode == "summary":
            changed = diff_view.changed_files(project_path)
            await self._send_chunked(channel, diff_view.render_summary(changed, claude_summary))
            return

        presentation = diff_view.render_diff(diff_view.capture_diff(project_path))
        for chunk in presentation.messages:
            await channel.send(chunk)
        if presentation.attachment is not None:
            await channel.send(
                file=discord.File(io.BytesIO(presentation.attachment), filename=presentation.attachment_name)
            )

    async def _send_chunked(self, channel, text: str) -> None:
        for i in range(0, len(text), MAX_MESSAGE_LENGTH):
            await channel.send(text[i : i + MAX_MESSAGE_LENGTH])

    # -- background loops -----------------------------------------------------

    async def _status_loop(self) -> None:
        while not self.is_closed():
            current = self._queue.current
            write_runtime_state(
                RuntimeState(
                    pid=os.getpid(),
                    started_at=self._started_at,
                    current=f"{current.project_alias}: {current.instruction[:80]}" if current else None,
                    queue_length=self._queue.pending_count,
                    paused=self._paused,
                )
            )
            await asyncio.sleep(STATUS_WRITE_INTERVAL_SECONDS)

    async def _heartbeat_loop(self) -> None:
        await self.wait_until_ready()
        while not self.is_closed():
            await asyncio.sleep(self.settings.heartbeat_interval_seconds)
            if self._channel is not None:
                await self._channel.send("\N{WHITE HEAVY CHECK MARK} claude-bridge 稼働中")
