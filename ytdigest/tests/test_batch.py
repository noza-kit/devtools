from __future__ import annotations

from datetime import datetime, timedelta, timezone

import responses

from ytdigest import batch
from ytdigest.discord_client import DISCORD_API_BASE
from ytdigest.twitch import API_BASE as TWITCH_API_BASE
from ytdigest.twitch import TOKEN_URL, TwitchClient
from ytdigest.youtube import YOUTUBE_FEED_URL

MESSAGES_URL = f"{DISCORD_API_BASE}/channels/555555/messages"


def _mock_twitch_token():
    responses.add(
        responses.POST, TOKEN_URL, json={"access_token": "tok", "expires_in": 3600}, status=200
    )


def _reply(id_, *, content, reference_id):
    return {
        "id": id_,
        "content": content,
        "author": {"bot": False},
        "message_reference": {"message_id": reference_id},
    }


def _twitch_client(secrets):
    return TwitchClient(client_id=secrets.twitch_client_id, client_secret=secrets.twitch_client_secret)


# -- process_dismiss_replies ----------------------------------------------------------


@responses.activate
def test_process_dismiss_replies_marks_item_dismissed(db, make_item, secrets):
    item_id = db.add_item(make_item())
    db.mark_notified(item_id, message_id="msg-1", number=1, notified_at="2026-08-01T00:00:00Z")
    responses.add(
        responses.GET, MESSAGES_URL, json=[_reply("2001", content="delete 1", reference_id="msg-1")], status=200
    )

    batch.process_dismiss_replies(db, secrets)

    assert db.get_item(item_id).status == "dismissed"
    assert db.get_meta("last_seen_message_id") == "2001"


@responses.activate
def test_process_dismiss_replies_ignores_wrong_number(db, make_item, secrets):
    item_id = db.add_item(make_item())
    db.mark_notified(item_id, message_id="msg-1", number=1, notified_at="2026-08-01T00:00:00Z")
    responses.add(
        responses.GET, MESSAGES_URL, json=[_reply("2001", content="delete 2", reference_id="msg-1")], status=200
    )

    batch.process_dismiss_replies(db, secrets)

    assert db.get_item(item_id).status == "pending"


@responses.activate
def test_process_dismiss_replies_untracks_live_item(db, make_item, secrets):
    item_id = db.add_item(make_item(platform="twitch", type="live", url="https://twitch.tv/streamer1"))
    db.mark_notified(item_id, message_id="msg-1", number=1, notified_at="2026-08-01T00:00:00Z")
    db.add_live_tracking("streamer1", item_id, "2026-08-01T00:00:00Z")
    responses.add(
        responses.GET, MESSAGES_URL, json=[_reply("2001", content="delete 1", reference_id="msg-1")], status=200
    )

    batch.process_dismiss_replies(db, secrets)

    assert db.get_item(item_id).status == "dismissed"
    assert db.get_live_tracking("streamer1") is None


@responses.activate
def test_process_dismiss_replies_uses_stored_cursor(db, secrets):
    db.set_meta("last_seen_message_id", "999")
    responses.add(responses.GET, MESSAGES_URL, json=[], status=200)

    batch.process_dismiss_replies(db, secrets)

    assert "after=999" in responses.calls[0].request.url


# -- process_ended_live_streams --------------------------------------------------------


@responses.activate
def test_process_ended_live_stream_becomes_vod(db, make_item, secrets):
    item_id = db.add_item(make_item(platform="twitch", type="live", url="https://twitch.tv/streamer1"))
    db.add_live_tracking("streamer1", item_id, "2026-08-01T00:00:00Z")

    _mock_twitch_token()
    responses.add(responses.GET, f"{TWITCH_API_BASE}/streams", json={"data": []}, status=200)
    responses.add(responses.GET, f"{TWITCH_API_BASE}/users", json={"data": [{"id": "1"}]}, status=200)
    responses.add(
        responses.GET,
        f"{TWITCH_API_BASE}/videos",
        json={
            "data": [
                {
                    "id": "vod1",
                    "title": "The stream",
                    "url": "https://www.twitch.tv/videos/vod1",
                    "thumbnail_url": "",
                    "created_at": "2026-08-01T02:00:00Z",
                    "published_at": "2026-08-01T02:00:00Z",
                }
            ]
        },
        status=200,
    )

    with _twitch_client(secrets) as twitch:
        batch.process_ended_live_streams(db, twitch)

    assert db.get_item(item_id).status == "archived"
    assert db.get_live_tracking("streamer1") is None
    vod_item = db.get_item_by_url("https://www.twitch.tv/videos/vod1")
    assert vod_item is not None
    assert vod_item.type == "vod"
    assert vod_item.status == "pending"


@responses.activate
def test_process_ended_live_stream_still_live_is_noop(db, make_item, secrets):
    item_id = db.add_item(make_item(platform="twitch", type="live", url="https://twitch.tv/streamer1"))
    db.add_live_tracking("streamer1", item_id, "2026-08-01T00:00:00Z")

    _mock_twitch_token()
    responses.add(
        responses.GET,
        f"{TWITCH_API_BASE}/streams",
        json={"data": [{"id": "s1", "user_login": "streamer1", "user_name": "Streamer1", "title": "t", "started_at": "x", "thumbnail_url": ""}]},
        status=200,
    )

    with _twitch_client(secrets) as twitch:
        batch.process_ended_live_streams(db, twitch)

    assert db.get_item(item_id).status == "pending"
    assert db.get_live_tracking("streamer1") is not None
    assert len(responses.calls) == 2  # token + streams only, no users/videos calls


@responses.activate
def test_process_ended_live_stream_no_vod_yet_keeps_tracking(db, make_item, secrets):
    item_id = db.add_item(make_item(platform="twitch", type="live", url="https://twitch.tv/streamer1"))
    db.add_live_tracking("streamer1", item_id, "2026-08-01T00:00:00Z")

    _mock_twitch_token()
    responses.add(responses.GET, f"{TWITCH_API_BASE}/streams", json={"data": []}, status=200)
    responses.add(responses.GET, f"{TWITCH_API_BASE}/users", json={"data": [{"id": "1"}]}, status=200)
    responses.add(responses.GET, f"{TWITCH_API_BASE}/videos", json={"data": []}, status=200)

    with _twitch_client(secrets) as twitch:
        batch.process_ended_live_streams(db, twitch)

    assert db.get_item(item_id).status == "pending"
    assert db.get_live_tracking("streamer1") is not None


def test_process_ended_live_stream_no_tracked_channels_is_noop(db, secrets):
    with _twitch_client(secrets) as twitch:
        batch.process_ended_live_streams(db, twitch)  # no HTTP calls, no responses mocked


# -- fetch_new_items ---------------------------------------------------------------------

SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/"
      xmlns="http://www.w3.org/2005/Atom">
 <entry>
  <id>yt:video:vid1</id>
  <yt:videoId>vid1</yt:videoId>
  <title>New Upload</title>
  <link rel="alternate" href="https://www.youtube.com/watch?v=vid1"/>
  <author><name>Example Channel</name></author>
  <published>2026-08-01T12:00:00+00:00</published>
  <updated>2026-08-01T13:00:00+00:00</updated>
  <media:group><media:thumbnail url="https://i.ytimg.com/vi/vid1/hqdefault.jpg"/></media:group>
 </entry>
</feed>
"""


@responses.activate
def test_fetch_new_items_adds_youtube_and_live_twitch(db, channels, secrets):
    responses.add(responses.GET, YOUTUBE_FEED_URL, body=SAMPLE_FEED, status=200)
    _mock_twitch_token()
    responses.add(
        responses.GET,
        f"{TWITCH_API_BASE}/streams",
        json={
            "data": [
                {
                    "id": "s1",
                    "user_login": "streamer1",
                    "user_name": "Streamer1",
                    "title": "Live now",
                    "started_at": "2026-08-01T00:00:00Z",
                    "thumbnail_url": "",
                }
            ]
        },
        status=200,
    )

    with _twitch_client(secrets) as twitch:
        batch.fetch_new_items(db, channels, twitch)

    yt_item = db.get_item_by_url("https://www.youtube.com/watch?v=vid1")
    assert yt_item is not None
    assert yt_item.status == "pending"

    live_items = [i for i in db.get_items_by_status("pending") if i.platform == "twitch"]
    assert len(live_items) == 1
    assert db.get_live_tracking("streamer1") is not None


@responses.activate
def test_fetch_new_items_skips_already_tracked_live_channel(db, channels, secrets, make_item):
    existing_id = db.add_item(make_item(platform="twitch", type="live", url="https://twitch.tv/streamer1/existing"))
    db.add_live_tracking("streamer1", existing_id, "2026-08-01T00:00:00Z")

    responses.add(responses.GET, YOUTUBE_FEED_URL, body="""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>""", status=200)
    _mock_twitch_token()
    responses.add(
        responses.GET,
        f"{TWITCH_API_BASE}/streams",
        json={
            "data": [
                {
                    "id": "s1",
                    "user_login": "streamer1",
                    "user_name": "Streamer1",
                    "title": "Live now",
                    "started_at": "2026-08-01T00:00:00Z",
                    "thumbnail_url": "",
                }
            ]
        },
        status=200,
    )

    with _twitch_client(secrets) as twitch:
        batch.fetch_new_items(db, channels, twitch)

    live_items = [i for i in db.get_items_by_status("pending") if i.platform == "twitch"]
    assert len(live_items) == 1
    assert live_items[0].id == existing_id


# -- send_new_item_notifications -----------------------------------------------------


@responses.activate
def test_send_new_item_notifications_posts_and_marks_notified(db, make_item, secrets):
    id1 = db.add_item(make_item(url="https://youtube.com/1"))
    id2 = db.add_item(make_item(url="https://youtube.com/2"))
    already_notified_id = db.add_item(make_item(url="https://youtube.com/3"))
    db.mark_notified(already_notified_id, message_id="old-msg", number=1, notified_at="2026-08-01T00:00:00Z")

    responses.add(responses.POST, secrets.discord_webhook_new, json={"id": "new-msg-id"}, status=200)

    batch.send_new_item_notifications(db, secrets)

    assert db.get_item(id1).notify_message_id == "new-msg-id"
    assert db.get_item(id2).notify_message_id == "new-msg-id"
    assert {db.get_item(id1).notify_number, db.get_item(id2).notify_number} == {1, 2}
    # the already-notified item wasn't touched again
    assert db.get_item(already_notified_id).notify_message_id == "old-msg"
    assert len(responses.calls) == 1


@responses.activate
def test_send_new_item_notifications_no_pending_makes_no_request(db, secrets):
    batch.send_new_item_notifications(db, secrets)
    assert len(responses.calls) == 0


# -- archive_stale_pending_items -------------------------------------------------------


@responses.activate
def test_archive_stale_pending_items_archives_old_items(db, make_item, secrets):
    old_ts = (datetime.now(timezone.utc) - timedelta(days=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
    item_id = db.add_item(make_item())
    db.mark_notified(item_id, message_id="m1", number=1, notified_at=old_ts)

    responses.add(responses.POST, secrets.discord_webhook_archive, json={"id": "archive-msg"}, status=200)

    batch.archive_stale_pending_items(db, secrets)

    assert db.get_item(item_id).status == "archived"
    assert len(responses.calls) == 1


@responses.activate
def test_archive_stale_pending_items_skips_recent(db, make_item, secrets):
    recent_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    item_id = db.add_item(make_item())
    db.mark_notified(item_id, message_id="m1", number=1, notified_at=recent_ts)

    batch.archive_stale_pending_items(db, secrets)

    assert db.get_item(item_id).status == "pending"
    assert len(responses.calls) == 0


# -- run() end-to-end -------------------------------------------------------------------


@responses.activate
def test_run_full_batch(db, channels, secrets):
    responses.add(responses.GET, MESSAGES_URL, json=[], status=200)
    _mock_twitch_token()
    responses.add(responses.GET, f"{TWITCH_API_BASE}/streams", json={"data": []}, status=200)
    responses.add(responses.GET, YOUTUBE_FEED_URL, body=SAMPLE_FEED, status=200)
    responses.add(responses.POST, secrets.discord_webhook_new, json={"id": "msg-1"}, status=200)

    batch.run(db, channels, secrets)

    yt_item = db.get_item_by_url("https://www.youtube.com/watch?v=vid1")
    assert yt_item is not None
    assert yt_item.notify_message_id == "msg-1"
