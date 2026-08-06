from __future__ import annotations

import pytest

from feedwatch import poller
from feedwatch.db import add_watch, connect, has_seen
from feedwatch.feeds import FeedEntry
from feedwatch.twitch import StreamInfo


class FakeNotify:
    def __init__(self):
        self.calls = []

    def __call__(self, message, channels=None, *, config=None):
        self.calls.append((message, channels, config))
        return {}


@pytest.fixture
def fake_notify(monkeypatch):
    fake = FakeNotify()
    monkeypatch.setattr(poller, "notify", fake)
    return fake


class FakeTwitchClient:
    def __init__(self, stream):
        self._stream = stream

    def get_live_stream(self, user_login):
        return self._stream


# --- check_rss_watch -------------------------------------------------------------


def test_check_rss_watch_notifies_new_entries_and_records_them(tmp_path, monkeypatch, fake_notify):
    db = tmp_path / "t.db"
    with connect(db) as conn:
        watch = add_watch(conn, kind="rss", source="https://feed.test/x.xml", name="Chan", tags=[])
        entries = [
            FeedEntry(item_id="v1", title="Video 1", link="https://x/v1"),
            FeedEntry(item_id="v2", title="Video 2", link="https://x/v2"),
        ]
        monkeypatch.setattr(poller, "fetch_entries", lambda url: entries)

        new_count = poller.check_rss_watch(conn, watch, channels=["desktop"])

        assert new_count == 2
        assert len(fake_notify.calls) == 2
        assert "Video 1" in fake_notify.calls[0][0]
        assert "https://x/v1" in fake_notify.calls[0][0]
        assert has_seen(conn, watch.id, "v1")
        assert has_seen(conn, watch.id, "v2")


def test_check_rss_watch_skips_already_seen_entries(tmp_path, monkeypatch, fake_notify):
    db = tmp_path / "t.db"
    with connect(db) as conn:
        watch = add_watch(conn, kind="rss", source="https://feed.test/x.xml", name="Chan", tags=[])
        entries = [FeedEntry(item_id="v1", title="Video 1", link="https://x/v1")]
        monkeypatch.setattr(poller, "fetch_entries", lambda url: entries)

        poller.check_rss_watch(conn, watch, channels=["desktop"])
        second_count = poller.check_rss_watch(conn, watch, channels=["desktop"])

        assert second_count == 0
        assert len(fake_notify.calls) == 1


def test_check_rss_watch_fetch_error_is_swallowed(tmp_path, monkeypatch, fake_notify):
    from feedwatch.feeds import FeedFetchError

    db = tmp_path / "t.db"
    with connect(db) as conn:
        watch = add_watch(conn, kind="rss", source="https://feed.test/x.xml", name="Chan", tags=[])

        def _raise(url):
            raise FeedFetchError("boom")

        monkeypatch.setattr(poller, "fetch_entries", _raise)

        assert poller.check_rss_watch(conn, watch, channels=["desktop"]) == 0
        assert fake_notify.calls == []


# --- check_twitch_watch ------------------------------------------------------------


def test_check_twitch_watch_notifies_new_stream_only_once(tmp_path, fake_notify):
    db = tmp_path / "t.db"
    with connect(db) as conn:
        watch = add_watch(conn, kind="twitch", source="somestreamer", name="Streamer", tags=[])
        stream = StreamInfo(stream_id="s1", title="Playing", user_name="SomeStreamer", user_login="somestreamer")
        client = FakeTwitchClient(stream)

        first = poller.check_twitch_watch(conn, watch, client, channels=["desktop"])
        second = poller.check_twitch_watch(conn, watch, client, channels=["desktop"])

        assert first == 1
        assert second == 0
        assert len(fake_notify.calls) == 1
        assert "Playing" in fake_notify.calls[0][0]
        assert "https://www.twitch.tv/somestreamer" in fake_notify.calls[0][0]


def test_check_twitch_watch_offline_does_not_notify(tmp_path, fake_notify):
    db = tmp_path / "t.db"
    with connect(db) as conn:
        watch = add_watch(conn, kind="twitch", source="somestreamer", name="Streamer", tags=[])
        client = FakeTwitchClient(None)

        count = poller.check_twitch_watch(conn, watch, client, channels=["desktop"])

        assert count == 0
        assert fake_notify.calls == []


def test_check_twitch_watch_new_broadcast_after_offline_notifies_again(tmp_path, fake_notify):
    db = tmp_path / "t.db"
    with connect(db) as conn:
        watch = add_watch(conn, kind="twitch", source="somestreamer", name="Streamer", tags=[])

        stream1 = StreamInfo(stream_id="s1", title="First", user_name="S", user_login="somestreamer")
        poller.check_twitch_watch(conn, watch, FakeTwitchClient(stream1), channels=["desktop"])

        # channel went offline then live again -> new stream id
        stream2 = StreamInfo(stream_id="s2", title="Second", user_name="S", user_login="somestreamer")
        count = poller.check_twitch_watch(conn, watch, FakeTwitchClient(stream2), channels=["desktop"])

        assert count == 1
        assert len(fake_notify.calls) == 2


# --- check_all ----------------------------------------------------------------------


def test_check_all_skips_twitch_watches_without_client(tmp_path, monkeypatch, fake_notify):
    db = tmp_path / "t.db"
    with connect(db) as conn:
        add_watch(conn, kind="rss", source="https://feed.test/x.xml", name="Chan", tags=[])
        add_watch(conn, kind="twitch", source="somestreamer", name="Streamer", tags=[])
        monkeypatch.setattr(poller, "fetch_entries", lambda url: [FeedEntry("v1", "V1", "https://x/v1")])

        notified = poller.check_all(conn, channels=["desktop"], twitch_client=None)

        assert notified == 1
        assert len(fake_notify.calls) == 1


# --- run_forever ----------------------------------------------------------------------


def test_run_forever_sleeps_between_cycles_but_not_after_the_last(feedwatch_home, monkeypatch, fake_notify):
    sleeps = []
    monkeypatch.setattr(poller.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(poller, "fetch_entries", lambda url: [])
    monkeypatch.delenv("TWITCH_CLIENT_ID", raising=False)
    monkeypatch.delenv("TWITCH_CLIENT_SECRET", raising=False)

    poller.run_forever(interval_seconds=5, channels=["desktop"], max_cycles=3)

    assert sleeps == [5, 5]
