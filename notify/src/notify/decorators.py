from __future__ import annotations

import functools
import time
from typing import Any, Callable, Mapping, Optional, TypeVar

from notify.core import notify

F = TypeVar("F", bound=Callable[..., Any])


def notify_on_complete(
    message: str = "処理完了",
    *,
    channels: list[str] = ["desktop"],
    notify_on_error: bool = True,
    config: Optional[Mapping[str, Any]] = None,
) -> Callable[[F], F]:
    """Send a notification when the decorated function finishes.

    Notifies on success with `message`, and (unless `notify_on_error=False`)
    also notifies on an exception before re-raising it unchanged - handy for
    long-running training scripts where you want to know about a crash too.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                if notify_on_error:
                    elapsed = time.monotonic() - start
                    notify(
                        f"{func.__name__} failed after {elapsed:.1f}s: {exc}",
                        channels,
                        config=config,
                    )
                raise
            elapsed = time.monotonic() - start
            notify(f"{message} ({func.__name__}, {elapsed:.1f}s)", channels, config=config)
            return result

        return wrapper

    return decorator
