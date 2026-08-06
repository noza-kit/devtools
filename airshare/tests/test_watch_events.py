from pathlib import Path

from airshare.watch_events import DebounceTracker


def test_temp_suffixes_never_tracked():
    tracker = DebounceTracker(debounce_seconds=1.0, now_fn=lambda: 0.0)
    tracker.notify_event(Path("a.tmp"))
    tracker.notify_event(Path("b.part"))
    tracker.notify_event(Path("c.crdownload"))
    assert len(tracker) == 0
    assert tracker.has_pending() is False


def test_notify_event_tracks_normal_file():
    tracker = DebounceTracker(debounce_seconds=1.0, now_fn=lambda: 0.0)
    tracker.notify_event(Path("photo.jpg"))
    assert len(tracker) == 1
    assert tracker.has_pending() is True


def test_ready_batch_empty_before_debounce_elapses():
    now = [0.0]
    tracker = DebounceTracker(debounce_seconds=3.0, now_fn=lambda: now[0])
    tracker.notify_event(Path("a.jpg"))
    now[0] = 1.0
    assert tracker.ready_batch() == []


def test_ready_batch_returns_settled_files():
    now = [0.0]
    tracker = DebounceTracker(debounce_seconds=3.0, now_fn=lambda: now[0])
    tracker.notify_event(Path("a.jpg"))
    now[0] = 3.5
    assert tracker.ready_batch() == [Path("a.jpg")]
    assert len(tracker) == 0  # consumed


def test_repeated_events_reset_the_debounce_window():
    now = [0.0]
    tracker = DebounceTracker(debounce_seconds=3.0, now_fn=lambda: now[0])
    tracker.notify_event(Path("a.jpg"))
    now[0] = 2.0
    tracker.notify_event(Path("a.jpg"))  # still being written -- resets the clock
    now[0] = 4.0  # 2s since the most recent event, still < 3s debounce
    assert tracker.ready_batch() == []
    now[0] = 5.5  # now 3.5s since the most recent event
    assert tracker.ready_batch() == [Path("a.jpg")]


def test_ready_batch_only_returns_settled_subset():
    now = [0.0]
    tracker = DebounceTracker(debounce_seconds=3.0, now_fn=lambda: now[0])
    tracker.notify_event(Path("old.jpg"))
    now[0] = 2.9
    tracker.notify_event(Path("new.jpg"))
    now[0] = 3.1  # old.jpg (3.1s ago) is settled; new.jpg (0.2s ago) is not
    ready = tracker.ready_batch()
    assert ready == [Path("old.jpg")]
    assert len(tracker) == 1
