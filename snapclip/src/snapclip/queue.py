from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal, Optional

Kind = Literal["text", "image"]


@dataclass(frozen=True)
class QueueItem:
    kind: Kind
    content: object  # str for kind="text"; PIL.Image.Image for kind="image"


class PasteQueue:
    """The single FIFO behind both snapclip features that talk about a
    "queue": Snap's stack-capture mode (each screenshot's generated
    Markdown/LaTeX markup text is pushed here after the file is saved)
    and Clip's FIFO paste (regular OS-clipboard copies detected by
    polling are pushed here too) share this one queue, so "copy A, snap
    a screenshot, copy B" pastes back A, the screenshot markup, then B
    in that order on three successive paste-hotkey presses."""

    def __init__(self) -> None:
        self._items: deque[QueueItem] = deque()

    def push(self, item: QueueItem) -> None:
        self._items.append(item)

    def pop_oldest(self) -> Optional[QueueItem]:
        return self._items.popleft() if self._items else None

    def pop_all(self) -> list[QueueItem]:
        items = list(self._items)
        self._items.clear()
        return items

    def peek_all(self) -> list[QueueItem]:
        return list(self._items)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
