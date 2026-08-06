from __future__ import annotations

from typing import Callable

from ytdigest.db import Item

MAX_MESSAGE_LENGTH = 2000

_NEW_ITEMS_HEADER = "\N{PUBLIC ADDRESS LOUDSPEAKER}\N{VARIATION SELECTOR-16} **新着コンテンツ**\n\n"
_NEW_ITEMS_FOOTER = "\n\n興味がなければ `delete 番号,番号` と返信してください(例: `delete 1,3`)。"

_ARCHIVE_HEADER = "\N{PACKAGE} **アーカイブ**\n\n"
_ARCHIVE_FOOTER = ""

_PLATFORM_LABEL = {"youtube": "YouTube", "twitch": "Twitch"}
_TYPE_LABEL = {"video": "動画", "live": "配信中", "vod": "配信アーカイブ"}


def _label(item: Item) -> str:
    platform = _PLATFORM_LABEL.get(item.platform, item.platform)
    kind = _TYPE_LABEL.get(item.type, item.type)
    return f"[{platform}/{kind}]"


def _new_item_line(number: int, item: Item) -> str:
    return f"**{number}.** {_label(item)} {item.channel_name} - {item.title}\n{item.url}"


def _archive_item_line(_number: int, item: Item) -> str:
    return f"\N{BULLET} {_label(item)} {item.channel_name} - {item.title}\n{item.url}"


def build_new_item_messages(items: list[Item]) -> list[tuple[list[Item], str]]:
    """Split `items` into one or more Discord message bodies (each within
    Discord's 2000-char limit), numbering restarting at 1 per message. Each
    item's assigned number is only meaningful together with the message it
    was sent in (see `db.mark_notified`)."""
    return _chunk_and_render(
        items, header=_NEW_ITEMS_HEADER, footer=_NEW_ITEMS_FOOTER, line_fn=_new_item_line
    )


def build_archive_messages(items: list[Item]) -> list[tuple[list[Item], str]]:
    """Split `items` into one or more archive-channel message bodies."""
    return _chunk_and_render(
        items, header=_ARCHIVE_HEADER, footer=_ARCHIVE_FOOTER, line_fn=_archive_item_line
    )


def _chunk_and_render(
    items: list[Item],
    *,
    header: str,
    footer: str,
    line_fn: Callable[[int, Item], str],
    max_length: int = MAX_MESSAGE_LENGTH,
) -> list[tuple[list[Item], str]]:
    def render(lines: list[str]) -> str:
        return f"{header}{(chr(10) * 2).join(lines)}{footer}" if lines else ""

    chunks: list[tuple[list[Item], str]] = []
    current_items: list[Item] = []
    current_lines: list[str] = []

    for item in items:
        line = line_fn(len(current_items) + 1, item)
        candidate = current_lines + [line]
        if len(render(candidate)) > max_length and current_items:
            chunks.append((current_items, render(current_lines)))
            current_items, current_lines = [], []
            line = line_fn(1, item)
            candidate = [line]
        current_items = current_items + [item]
        current_lines = candidate

    if current_items:
        chunks.append((current_items, render(current_lines)))

    return chunks
