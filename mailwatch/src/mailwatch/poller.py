from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from notify import notify

from mailwatch.attachments import save_attachments
from mailwatch.auth import AuthError, load_credentials, refresh_if_needed
from mailwatch.gmail_client import GmailApiError, get_message, list_message_ids
from mailwatch.message import ParsedMessage, parse_message
from mailwatch.rules import Rule, WatchConfig
from mailwatch.store import SeenStore

logger = logging.getLogger("mailwatch")


def _format_notification(rule: Rule, message: ParsedMessage) -> str:
    if message.date_header:
        received = message.date_header
    else:
        received = datetime.fromtimestamp(message.internal_date_ms / 1000, tz=timezone.utc).isoformat()
    return (
        f"[mailwatch] ルール「{rule.name}」に一致するメールを検知しました\n"
        f"差出人: {message.from_header}\n"
        f"件名: {message.subject}\n"
        f"受信日時: {received}"
    )


def poll_once(access_token: str, config: WatchConfig, store: SeenStore) -> int:
    """Run one poll cycle: list recent messages, skip already-seen ones,
    evaluate rules on the rest, notify + save attachments for matches, and
    record every message it looked at (matched or not) as seen. Returns the
    number of new messages processed."""
    try:
        ids = list_message_ids(access_token, config.gmail_query)
    except GmailApiError as exc:
        logger.error("Gmail message list failed: %s", exc)
        return 0

    new_ids = [mid for mid in ids if not store.is_seen(mid)]
    processed = 0
    for mid in new_ids:
        try:
            raw = get_message(access_token, mid)
        except GmailApiError as exc:
            logger.error("Gmail message fetch failed for %s: %s", mid, exc)
            continue

        message = parse_message(raw)
        matched = [rule for rule in config.rules if rule.matches(message)]

        for rule in matched:
            results = notify(
                _format_notification(rule, message), channels=rule.channels, config=config.notify_config
            )
            for channel, result in results.items():
                if not result.ok:
                    logger.warning("notify: rule %r channel %r failed: %s", rule.name, channel, result.error)

            if rule.save_attachments and message.attachments:
                try:
                    saved = save_attachments(access_token, message, Path(rule.attachment_dir))
                    logger.info(
                        "Saved %d attachment(s) for message %s (rule %r): %s",
                        len(saved), mid, rule.name, saved,
                    )
                except GmailApiError as exc:
                    logger.error("Attachment download failed for message %s: %s", mid, exc)

        store.mark_seen(mid, [r.name for r in matched])
        processed += 1

    return processed


def run_forever(
    *,
    credentials_path: Path,
    token_path: Path,
    config: WatchConfig,
    store: SeenStore,
    interval_seconds: int,
) -> None:
    creds = load_credentials(credentials_path, token_path, interactive=True)

    logger.info("mailwatch started (interval=%ds, rules=%d)", interval_seconds, len(config.rules))
    while True:
        try:
            creds = refresh_if_needed(creds, token_path)
        except AuthError as exc:
            logger.error("%s", exc)
            time.sleep(interval_seconds)
            continue

        try:
            n = poll_once(creds.token, config, store)
            if n:
                logger.info("Processed %d new message(s)", n)
        except Exception:
            logger.exception("Unexpected error during poll cycle")

        time.sleep(interval_seconds)
