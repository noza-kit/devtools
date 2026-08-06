from __future__ import annotations

import base64

import pytest
import responses

from mailwatch.gmail_client import (
    GMAIL_API_BASE,
    GmailApiError,
    get_attachment_data,
    get_message,
    list_message_ids,
)

TOKEN = "fake-access-token"


@responses.activate
def test_list_message_ids_single_page():
    responses.add(
        responses.GET,
        f"{GMAIL_API_BASE}/messages",
        json={"messages": [{"id": "a"}, {"id": "b"}]},
        status=200,
    )

    ids = list_message_ids(TOKEN, "in:inbox")

    assert ids == ["a", "b"]
    assert responses.calls[0].request.headers["Authorization"] == f"Bearer {TOKEN}"


@responses.activate
def test_list_message_ids_paginates():
    responses.add(
        responses.GET,
        f"{GMAIL_API_BASE}/messages",
        json={"messages": [{"id": "a"}], "nextPageToken": "p2"},
        status=200,
    )
    responses.add(
        responses.GET,
        f"{GMAIL_API_BASE}/messages",
        json={"messages": [{"id": "b"}]},
        status=200,
    )

    ids = list_message_ids(TOKEN, "in:inbox", max_results=10)

    assert ids == ["a", "b"]
    assert len(responses.calls) == 2


@responses.activate
def test_list_message_ids_stops_at_max_results():
    responses.add(
        responses.GET,
        f"{GMAIL_API_BASE}/messages",
        json={"messages": [{"id": "a"}, {"id": "b"}], "nextPageToken": "p2"},
        status=200,
    )

    ids = list_message_ids(TOKEN, "in:inbox", max_results=2)

    assert ids == ["a", "b"]
    assert len(responses.calls) == 1


@responses.activate
def test_get_message_error_raises(no_sleep):
    responses.add(
        responses.GET,
        f"{GMAIL_API_BASE}/messages/msg1",
        status=404,
        body="not found",
    )

    with pytest.raises(GmailApiError):
        get_message(TOKEN, "msg1")


@responses.activate
def test_get_attachment_data_decodes_base64url():
    raw_bytes = b"hello attachment"
    encoded = base64.urlsafe_b64encode(raw_bytes).decode("ascii").rstrip("=")
    responses.add(
        responses.GET,
        f"{GMAIL_API_BASE}/messages/msg1/attachments/att1",
        json={"size": len(raw_bytes), "data": encoded},
        status=200,
    )

    data = get_attachment_data(TOKEN, "msg1", "att1")

    assert data == raw_bytes
