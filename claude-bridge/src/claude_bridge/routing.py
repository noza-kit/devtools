from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Optional

from claude_bridge.config import Settings, find_project
from claude_bridge.guard import detect_dangerous
from claude_bridge.message_parse import parse_directives

STOP_WORDS = {"stop", "ストップ", "中止", "中断"}
CONFIRM_WORDS = {"yes", "はい"}
PAUSE_WORDS = {"終了", "shutdown", "exit"}
RESUME_WORDS = {"起動", "start", "resume"}
USAGE_WORDS = {"usage", "使用量", "コスト", "cost"}


@dataclass(frozen=True)
class IncomingMessage:
    author_id: str
    channel_id: str
    message_id: str
    content: str


@dataclass(frozen=True)
class PendingConfirmation:
    project_alias: str
    mode: str
    instruction: str
    reasons: list[str]


@dataclass(frozen=True)
class Decision:
    """What `on_message` should do about one incoming Discord message.
    `kind` is one of: ignore / notice / unknown_project / cancel /
    await_confirmation / confirmation_declined / run / pause / resume / usage.

    `ignore` never gets a reply (used for the wrong-channel/wrong-sender
    filter, so unauthorized senders get no sign the bot is even there).
    `notice` is a reply-only, no-op response (e.g. "already paused")."""

    kind: str
    reply: Optional[str] = None
    pending: Optional[PendingConfirmation] = None
    project_alias: Optional[str] = None
    mode: Optional[str] = None
    instruction: Optional[str] = None


def decide(
    msg: IncomingMessage,
    settings: Settings,
    *,
    allowed_channel_id: str,
    allowed_user_ids: FrozenSet[str],
    pending: Optional[PendingConfirmation],
    has_running_task: bool,
    is_paused: bool,
) -> Decision:
    if msg.channel_id != allowed_channel_id or msg.author_id not in allowed_user_ids:
        return Decision(kind="ignore")

    stripped = msg.content.strip()

    if pending is not None:
        if stripped.lower() in CONFIRM_WORDS:
            return Decision(
                kind="run",
                project_alias=pending.project_alias,
                mode=pending.mode,
                instruction=pending.instruction,
            )
        return Decision(
            kind="confirmation_declined", reply="確認がキャンセルされました。指示は実行されません。"
        )

    # Pause/resume are checked before the paused-gate below so `resume` can
    # actually un-pause, and take priority over everything except a pending
    # confirmation reply (handled above).
    if stripped.lower() in RESUME_WORDS:
        if is_paused:
            return Decision(kind="resume", reply="再開しました。指示を受け付けます。")
        return Decision(kind="notice", reply="既に稼働中です。")

    if stripped.lower() in PAUSE_WORDS:
        if is_paused:
            return Decision(kind="notice", reply="既に停止中です。")
        return Decision(
            kind="pause", reply="指示の受け付けを停止します。`起動` と送信すると再開します。"
        )

    if stripped.lower() in USAGE_WORDS:
        return Decision(kind="usage")

    if is_paused:
        return Decision(kind="notice", reply="現在停止中です。`起動` と送信すると再開します。")

    if stripped.lower() in STOP_WORDS:
        if not has_running_task:
            return Decision(kind="ignore")
        return Decision(kind="cancel")

    parsed = parse_directives(msg.content)
    if not parsed.instruction:
        return Decision(kind="ignore")

    project_alias = parsed.project_alias or settings.default_project
    if project_alias is None or find_project(settings, project_alias) is None:
        available = ", ".join(p.alias for p in settings.projects) or "(なし)"
        example = settings.projects[0].alias if settings.projects else "alias"
        return Decision(
            kind="unknown_project",
            reply=(
                f"プロジェクトを指定してください(例: `project: {example}`)。"
                f"登録済みプロジェクト: {available}"
            ),
        )

    mode = parsed.mode or settings.default_mode

    reasons = detect_dangerous(parsed.instruction)
    if reasons:
        return Decision(
            kind="await_confirmation",
            reply=(
                "この指示には破壊的な操作が含まれている可能性があります("
                + ", ".join(reasons)
                + ")。実行してよければ `yes` と返信してください。"
            ),
            pending=PendingConfirmation(
                project_alias=project_alias,
                mode=mode,
                instruction=parsed.instruction,
                reasons=reasons,
            ),
        )

    return Decision(kind="run", project_alias=project_alias, mode=mode, instruction=parsed.instruction)
