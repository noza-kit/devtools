from __future__ import annotations

import pytest
import responses

from ytdigest.discord_client import (
    DISCORD_API_BASE,
    DiscordError,
    fetch_reply_messages,
    parse_dismiss_numbers,
    post_webhook,
)

WEBHOOK_URL = "https://discord.com/api/webhooks/123/abc"
CHANNEL_ID = "999888777"


# -- post_webhook -------------------------------------------------------------------


@responses.activate
def test_post_webhook_returns_message_id():
    responses.add(responses.POST, WEBHOOK_URL, json={"id": "111222333"}, status=200)

    message_id = post_webhook(WEBHOOK_URL, "hello")

    assert message_id == "111222333"
    request = responses.calls[0].request
    assert "wait=true" in request.url


@responses.activate
def test_post_webhook_error_status_raises(no_sleep):
    responses.add(responses.POST, WEBHOOK_URL, status=400, body="bad request")

    with pytest.raises(DiscordError):
        post_webhook(WEBHOOK_URL, "hello")


def test_post_webhook_too_long_raises_without_request():
    with pytest.raises(DiscordError):
        post_webhook(WEBHOOK_URL, "x" * 2001)


# -- fetch_reply_messages ------------------------------------------------------------


def _msg(id_, *, content="", bot=False, reference_id=None):
    msg = {"id": id_, "content": content, "author": {"bot": bot}}
    if reference_id:
        msg["message_reference"] = {"message_id": reference_id}
    return msg


@responses.activate
def test_fetch_reply_messages_filters_bot_and_non_reply(no_sleep):
    responses.add(
        responses.GET,
        f"{DISCORD_API_BASE}/channels/{CHANNEL_ID}/messages",
        json=[
            _msg("3", content="delete 1", reference_id="1"),
            _msg("2", content="unrelated chatter"),
            _msg("1", content="bot notification", bot=True),
        ],
        status=200,
    )

    replies, last_seen = fetch_reply_messages("bot-token", CHANNEL_ID)

    assert len(replies) == 1
    assert replies[0].message_id == "3"
    assert replies[0].referenced_message_id == "1"
    assert replies[0].content == "delete 1"
    assert last_seen == "3"


@responses.activate
def test_fetch_reply_messages_sends_bot_authorization(no_sleep):
    responses.add(
        responses.GET, f"{DISCORD_API_BASE}/channels/{CHANNEL_ID}/messages", json=[], status=200
    )

    fetch_reply_messages("my-bot-token", CHANNEL_ID)

    request = responses.calls[0].request
    assert request.headers["Authorization"] == "Bot my-bot-token"


@responses.activate
def test_fetch_reply_messages_paginates(no_sleep):
    page1 = [_msg(str(i), content=f"delete {i}", reference_id="0") for i in range(1, 101)]
    page2 = [_msg("101", content="delete 1", reference_id="0")]
    responses.add(
        responses.GET, f"{DISCORD_API_BASE}/channels/{CHANNEL_ID}/messages", json=page1, status=200
    )
    responses.add(
        responses.GET, f"{DISCORD_API_BASE}/channels/{CHANNEL_ID}/messages", json=page2, status=200
    )

    replies, last_seen = fetch_reply_messages("bot-token", CHANNEL_ID)

    assert len(replies) == 101
    assert len(responses.calls) == 2
    second_request_url = responses.calls[1].request.url
    assert "after=100" in second_request_url
    assert last_seen == "101"


@responses.activate
def test_fetch_reply_messages_uses_after_param(no_sleep):
    responses.add(
        responses.GET, f"{DISCORD_API_BASE}/channels/{CHANNEL_ID}/messages", json=[], status=200
    )

    fetch_reply_messages("bot-token", CHANNEL_ID, after="555")

    assert "after=555" in responses.calls[0].request.url


@responses.activate
def test_fetch_reply_messages_no_new_messages_returns_after_unchanged(no_sleep):
    responses.add(
        responses.GET, f"{DISCORD_API_BASE}/channels/{CHANNEL_ID}/messages", json=[], status=200
    )

    replies, last_seen = fetch_reply_messages("bot-token", CHANNEL_ID, after="555")

    assert replies == []
    assert last_seen == "555"


@responses.activate
def test_fetch_reply_messages_advances_cursor_past_non_reply_tail(no_sleep):
    responses.add(
        responses.GET,
        f"{DISCORD_API_BASE}/channels/{CHANNEL_ID}/messages",
        json=[
            _msg("2", content="delete 1", reference_id="1"),
            _msg("3", content="just chatting, not a reply"),
        ],
        status=200,
    )

    replies, last_seen = fetch_reply_messages("bot-token", CHANNEL_ID)

    assert len(replies) == 1
    assert last_seen == "3"


@responses.activate
def test_fetch_reply_messages_error_status_raises(no_sleep):
    responses.add(
        responses.GET, f"{DISCORD_API_BASE}/channels/{CHANNEL_ID}/messages", status=403, body="forbidden"
    )

    with pytest.raises(DiscordError):
        fetch_reply_messages("bot-token", CHANNEL_ID)


# -- parse_dismiss_numbers ------------------------------------------------------------


@pytest.mark.parametrize(
    "content,expected",
    [
        ("delete 1,3", [1, 3]),
        ("delete 1, 3", [1, 3]),
        ("delete 1 3", [1, 3]),
        ("DELETE 2", [2]),
        ("Delete   7,  8, 9", [7, 8, 9]),
        ("no command here", []),
        ("", []),
        ("please delete 4", [4]),
    ],
)
def test_parse_dismiss_numbers(content, expected):
    assert parse_dismiss_numbers(content) == expected
