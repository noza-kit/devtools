from snapclip.config import Settings
from snapclip.queue import PasteQueue
from snapclip.scrollcapture import ScrollCaptureSession, ScrollCaptureState


def _fake_stitch(frames):
    # a deterministic stand-in for stitch_vertical: just tag the frame count
    from PIL import Image

    img = Image.new("RGB", (10, 10 * len(frames)))
    img.info["frame_count"] = len(frames)
    return img


def _session(fake_capture, settings, queue, now_values=None):
    times = iter(now_values or [0.0] * 100)
    return ScrollCaptureSession(
        fake_capture, settings, queue, stitch_fn=_fake_stitch, min_capture_interval=0.1, now_fn=lambda: next(times)
    )


def test_full_flow_produces_stitched_file(fake_capture, settings: Settings, queue: PasteQueue):
    session = _session(fake_capture, settings, queue, now_values=[0.0, 0.5, 1.0])
    session.start()
    assert session.state == ScrollCaptureState.SELECTING_REGION

    session.on_mouse_down((10, 10))
    session.on_mouse_up((110, 210))
    assert session.state == ScrollCaptureState.CAPTURING
    assert fake_capture.region_calls == [(10, 10, 110, 210)]  # first frame captured on region confirm

    session.on_scroll()
    session.on_scroll()

    path = session.finish()
    assert path is not None
    assert path.exists()
    assert session.state == ScrollCaptureState.IDLE


def test_tiny_drag_is_ignored_as_accidental_click(fake_capture, settings: Settings, queue: PasteQueue):
    session = _session(fake_capture, settings, queue)
    session.start()
    session.on_mouse_down((10, 10))
    session.on_mouse_up((12, 12))  # 2x2 px drag, below the minimum
    assert session.state == ScrollCaptureState.SELECTING_REGION
    assert fake_capture.region_calls == []


def test_finish_without_region_returns_none(fake_capture, settings: Settings, queue: PasteQueue):
    session = _session(fake_capture, settings, queue)
    session.start()
    result = session.finish()
    assert result is None
    assert len(queue) == 0


def test_finish_when_idle_returns_none(fake_capture, settings: Settings, queue: PasteQueue):
    session = _session(fake_capture, settings, queue)
    assert session.finish() is None


def test_scroll_before_region_confirmed_is_ignored(fake_capture, settings: Settings, queue: PasteQueue):
    session = _session(fake_capture, settings, queue)
    session.start()
    session.on_scroll()  # no region yet
    assert fake_capture.region_calls == []


def test_debounce_drops_rapid_scroll_events(fake_capture, settings: Settings, queue: PasteQueue):
    # times: region-confirm capture at t=0, then two scrolls 0.01s apart (should debounce to 1 extra capture)
    session = _session(fake_capture, settings, queue, now_values=[0.0, 0.01, 0.02, 5.0])
    session.start()
    session.on_mouse_down((0, 0))
    session.on_mouse_up((100, 100))  # captures frame #1 at t=0.0
    session.on_scroll()  # t=0.01, within 0.1s of last capture -> debounced, no new frame
    session.on_scroll()  # t=0.02, still debounced
    assert len(fake_capture.region_calls) == 1

    path = session.finish()
    assert path is not None


def test_pushes_markup_to_queue_on_finish(fake_capture, settings: Settings, queue: PasteQueue):
    session = _session(fake_capture, settings, queue, now_values=[0.0, 1.0])
    session.start()
    session.on_mouse_down((0, 0))
    session.on_mouse_up((50, 50))
    session.finish()
    items = queue.peek_all()
    assert len(items) == 1
    assert items[0].content.startswith("![")


def test_starting_again_while_capturing_is_ignored(fake_capture, settings: Settings, queue: PasteQueue):
    session = _session(fake_capture, settings, queue)
    session.start()
    session.on_mouse_down((0, 0))
    session.on_mouse_up((50, 50))
    assert session.state == ScrollCaptureState.CAPTURING
    session.start()  # should be a no-op; already capturing
    assert session.state == ScrollCaptureState.CAPTURING
