from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet, Optional

from claude_bridge.config import Settings, find_project
from claude_bridge.guard import detect_dangerous
from claude_bridge.message_parse import parse_directives

STOP_WORDS = {"stop", "ストップ", "中止", "中断"}
CONFIRM_WORDS = {"yes", "はい"}


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
    `kind` is one of: ignore / unknown_project / cancel / await_confirmation
    / confirmation_declined / run."""

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
