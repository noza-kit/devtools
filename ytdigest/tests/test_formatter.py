from __future__ import annotations

from ytdigest.formatter import MAX_MESSAGE_LENGTH, build_archive_messages, build_new_item_messages


def test_build_new_item_messages_single_chunk(make_item):
    items = [
        make_item(url="https://youtube.com/1", title="Video One"),
        make_item(url="https://youtube.com/2", title="Video Two", platform="twitch", type="live"),
    ]

    chunks = build_new_item_messages(items)

    assert len(chunks) == 1
    chunk_items, text = chunks[0]
    assert chunk_items == items
    assert "**1.**" in text
    assert "**2.**" in text
    assert "Video One" in text
    assert "Video Two" in text
    assert "delete" in text
    assert len(text) <= MAX_MESSAGE_LENGTH


def test_build_new_item_messages_empty_returns_no_chunks():
    assert build_new_item_messages([]) == []


def test_build_new_item_messages_numbers_restart_per_chunk(make_item):
    # Force a split by using a tiny max_length via many long-titled items.
    items = [make_item(url=f"https://youtube.com/{i}", title="X" * 900) for i in range(4)]

    chunks = build_new_item_messages(items)

    assert len(chunks) > 1
    for chunk_items, text in chunks:
        assert "**1.**" in text
        assert len(text) <= MAX_MESSAGE_LENGTH

    # every item still appears exactly once across all chunks
    all_items = [item for chunk_items, _ in chunks for item in chunk_items]
    assert all_items == items


def test_build_archive_messages_uses_bullets_not_numbers(make_item):
    items = [make_item(url="https://youtube.com/1", title="Archived Video")]

    chunks = build_archive_messages(items)

    assert len(chunks) == 1
    _, text = chunks[0]
    assert "\N{BULLET}" in text
    assert "**1.**" not in text
    assert "delete" not in text


def test_build_archive_messages_empty_returns_no_chunks():
    assert build_archive_messages([]) == []


def test_platform_and_type_labels_rendered(make_item):
    item = make_item(platform="twitch", type="vod", title="Stream Replay")
    chunks = build_new_item_messages([item])

    _, text = chunks[0]
    assert "[Twitch/配信アーカイブ]" in text
