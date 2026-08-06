from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from ytdigest import discord_client, formatter, youtube
from ytdigest.config import Channels, Secrets
from ytdigest.db import Database, Item
from ytdigest.twitch import TwitchClient, TwitchError

logger = logging.getLogger("ytdigest")

# How long a notified-but-undismissed item waits before it's treated as "of
# interest" and moved to the archive channel.
STALE_AFTER_DAYS = 3


def run(db: Database, channels: Channels, secrets: Secrets) -> None:
    """Run one full daily batch: steps 1-6 from the design doc, in order."""
    with TwitchClient(client_id=secrets.twitch_client_id, client_secret=secrets.twitch_client_secret) as twitch:
        process_dismiss_replies(db, secrets)
        process_ended_live_streams(db, twitch)
        fetch_new_items(db, channels, twitch)
    send_new_item_notifications(db, secrets)
    archive_stale_pending_items(db, secrets)


# -- step 1+2: read replies to the last notification, apply dismiss commands --------


def process_dismiss_replies(db: Database, secrets: Secrets) -> None:
    after = db.get_meta("last_seen_message_id")
    replies, last_seen = discord_client.fetch_reply_messages(
        secrets.discord_bot_token, secrets.discord_new_channel_id, after=after
    )

    for reply in replies:
        for number in discord_client.parse_dismiss_numbers(reply.content):
            item = db.get_item_by_notify(reply.referenced_message_id, number)
            if item is None or item.status != "pending":
                continue
            db.set_status(item.id, "dismissed")
            _untrack_live(db, item)

    if last_seen and last_seen != after:
        db.set_meta("last_seen_message_id", last_seen)


def _untrack_live(db: Database, item: Item) -> None:
    if item.type != "live":
        return
    for tracking in db.list_live_tracking():
        if tracking.item_id == item.id:
            db.remove_live_tracking(tracking.channel_name)
            return


# -- step 3: detect ended live streams, convert them to VODs ------------------------


def process_ended_live_streams(db: Database, twitch: TwitchClient) -> None:
    tracked = db.list_live_tracking()
    if not tracked:
        return

    try:
        live_now = twitch.get_live_streams(t.channel_name for t in tracked)
    except TwitchError as exc:
        logger.warning("skipping ended-live-stream check: %s", exc)
        return

    for tracking in tracked:
        if tracking.channel_name.lower() in live_now:
            continue  # still live

        item = db.get_item(tracking.item_id)
        if item is None:
            db.remove_live_tracking(tracking.channel_name)
            continue

        try:
            vod = twitch.get_latest_vod(tracking.channel_name, after=tracking.started_at)
        except TwitchError as exc:
            logger.warning("failed to fetch VOD for %s: %s", tracking.channel_name, exc)
            continue

        if vod is None:
            logger.info("live ended for %s but no VOD available yet; retrying next run", tracking.channel_name)
            continue

        db.add_item(
            Item(
                platform="twitch",
                type="vod",
                title=vod.title,
                channel_name=item.channel_name,
                url=vod.url,
                thumbnail_url=vod.thumbnail_url,
                published_at=vod.published_at,
            )
        )
        db.set_status(item.id, "archived")
        db.remove_live_tracking(tracking.channel_name)


# -- step 4: fetch new YouTube uploads and newly-started Twitch live streams --------


def fetch_new_items(db: Database, channels: Channels, twitch: TwitchClient) -> None:
    for yt_channel in channels.youtube:
        try:
            videos = youtube.fetch_channel_videos(yt_channel.channel_id, channel_name=yt_channel.name)
        except youtube.YouTubeError as exc:
            logger.warning("skipping YouTube channel %s: %s", yt_channel.channel_id, exc)
            continue

        for video in videos:
            db.add_item(
                Item(
                    platform="youtube",
                    type="video",
                    title=video.title,
                    channel_name=video.channel_name,
                    url=video.url,
                    thumbnail_url=video.thumbnail_url,
                    published_at=video.published_at,
                )
            )

    if not channels.twitch:
        return

    try:
        live_streams = twitch.get_live_streams(c.login for c in channels.twitch)
    except TwitchError as exc:
        logger.warning("skipping Twitch live check: %s", exc)
        return

    for tc in channels.twitch:
        stream = live_streams.get(tc.login.lower())
        if stream is None:
            continue
        if db.get_live_tracking(tc.login) is not None:
            continue  # already notified/tracked for this ongoing stream

        item_id = db.add_item(
            Item(
                platform="twitch",
                type="live",
                title=stream.title,
                channel_name=tc.name,
                url=f"https://www.twitch.tv/{tc.login}?sid={stream.stream_id}",
                thumbnail_url=stream.thumbnail_url,
                published_at=stream.started_at,
            )
        )
        if item_id is not None:
            db.add_live_tracking(tc.login, item_id, stream.started_at)


# -- step 5: notify the new-content channel about newly-added pending items ---------


def send_new_item_notifications(db: Database, secrets: Secrets) -> None:
    pending = [item for item in db.get_items_by_status("pending") if item.notified_at is None]
    if not pending:
        return

    now = _now_iso()
    for chunk_items, text in formatter.build_new_item_messages(pending):
        message_id = discord_client.post_webhook(secrets.discord_webhook_new, text)
        for number, item in enumerate(chunk_items, start=1):
            db.mark_notified(item.id, message_id=message_id, number=number, notified_at=now)


# -- step 6: sweep pending items nobody dismissed in time, post them to archive -----


def archive_stale_pending_items(db: Database, secrets: Secrets) -> None:
    cutoff = _now_iso(offset=timedelta(days=-STALE_AFTER_DAYS))
    stale = db.get_stale_pending_items(cutoff)
    if not stale:
        return

    for chunk_items, text in formatter.build_archive_messages(stale):
        discord_client.post_webhook(secrets.discord_webhook_archive, text)
        for item in chunk_items:
            db.set_status(item.id, "archived")


def _now_iso(*, offset: Optional[timedelta] = None) -> str:
    now = datetime.now(timezone.utc)
    if offset is not None:
        now += offset
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")
