import time

from uzbridge.metrics import LatencyTracker, MetricsLogger, RateMeter


def test_rate_meter_fps_with_no_or_one_sample():
    meter = RateMeter()
    assert meter.fps == 0.0
    meter.tick()
    assert meter.fps == 0.0


def test_rate_meter_reports_positive_fps_after_ticks():
    meter = RateMeter(window=5)
    for _ in range(4):
        meter.tick()
        time.sleep(0.01)
    assert meter.fps > 0


def test_rate_meter_window_bounds_sample_count():
    meter = RateMeter(window=3)
    for _ in range(10):
        meter.tick()
    assert len(meter._timestamps) == 3


def test_latency_tracker_records_and_averages():
    tracker = LatencyTracker()
    sent_at = time.time()
    time.sleep(0.05)
    latency = tracker.record(sent_at)
    assert latency >= 0.05
    assert tracker.avg_ms >= 50


def test_latency_tracker_avg_ms_empty_is_zero():
    tracker = LatencyTracker()
    assert tracker.avg_ms == 0.0


def test_metrics_logger_record_frame_updates_rate_and_latency():
    logger = MetricsLogger(interval=999)
    logger.record_frame(time.time())
    assert logger.rate.fps == 0.0  # only one tick so far
    assert logger.latency.avg_ms >= 0
