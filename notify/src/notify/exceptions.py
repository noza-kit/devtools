from __future__ import annotations


class NotifyError(Exception):
    """Raised when a channel fails to deliver a notification."""


class NotifyConfigError(NotifyError):
    """Raised when a channel's required webhook URL/token is not configured."""
