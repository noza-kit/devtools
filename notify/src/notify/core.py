from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from notify.channels import CHANNELS

logger = logging.getLogger("notify")


@dataclass
class ChannelResult:
    """Outcome of sending a notification through one channel."""

    channel: str
    ok: bool
    error: Optional[str] = None


def notify(
    message: str,
    channels: list[str] = ["desktop"],
    *,
    config: Optional[Mapping[str, Any]] = None,
) -> dict[str, ChannelResult]:
    """Send `message` to each channel in `channels`.

    Never raises: an unknown channel name or a delivery failure is recorded
    in the returned ChannelResult instead, so callers (and notify_on_complete)
    can rely on this not crashing whatever it's notifying about.
    """
    results: dict[str, ChannelResult] = {}
    for channel in channels:
        handler = CHANNELS.get(channel)
        if handler is None:
            logger.warning("notify: unknown channel %r", channel)
            results[channel] = ChannelResult(channel, False, f"unknown channel: {channel!r}")
            continue
        try:
            handler(message, config)
        except Exception as exc:
            logger.warning("notify: %s channel failed: %s", channel, exc)
            results[channel] = ChannelResult(channel, False, str(exc))
        else:
            results[channel] = ChannelResult(channel, True)
    return results
