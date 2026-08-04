from __future__ import annotations

import json
import logging
import threading

import cv2
import numpy as np
import zmq

from uzbridge import protocol
from uzbridge.config import ServerConfig
from uzbridge.metrics import MetricsLogger
from uzbridge.pipeline import Pipeline

logger = logging.getLogger(__name__)


class BridgeServer:
    """Receives JPEG frames over SUB, runs them through a Pipeline, and
    serves the latest result to REQ clients (e.g. Unity) over REP."""

    def __init__(self, config: ServerConfig, pipeline: Pipeline):
        self.config = config
        self.pipeline = pipeline
        self.metrics = MetricsLogger(interval=config.log_interval)
        self._latest_result: dict | None = None
        self._stop_event = threading.Event()

        self.context = zmq.Context()

        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.setsockopt(zmq.SUBSCRIBE, protocol.TOPIC_FRAME)
        self.sub_socket.bind(config.sub_address)

        self.rep_socket = self.context.socket(zmq.REP)
        self.rep_socket.bind(config.rep_address)

        self.poller = zmq.Poller()
        self.poller.register(self.sub_socket, zmq.POLLIN)
        self.poller.register(self.rep_socket, zmq.POLLIN)

    def _handle_frame(self) -> None:
        parts = self.sub_socket.recv_multipart()
        # Drain any backlog so we always process the most recently sent
        # frame instead of falling behind if processing is slower than
        # the send rate.
        while True:
            try:
                parts = self.sub_socket.recv_multipart(flags=zmq.NOBLOCK)
            except zmq.Again:
                break

        frame_msg = protocol.decode_frame(parts)
        jpeg_array = np.frombuffer(frame_msg.jpeg_bytes, dtype=np.uint8)
        image = cv2.imdecode(jpeg_array, cv2.IMREAD_COLOR)
        if image is None:
            logger.warning("Failed to decode frame %s", frame_msg.frame_id)
            return

        results = self.pipeline.process(image)
        self._latest_result = {
            "frame_id": frame_msg.frame_id,
            "timestamp": frame_msg.timestamp,
            "results": results,
        }
        self.metrics.record_frame(frame_msg.timestamp)

    def _handle_request(self) -> None:
        request = self.rep_socket.recv()
        protocol.decode_request(request)  # currently informational only
        if self._latest_result is None:
            payload = {"status": "no_result"}
        else:
            payload = {"status": "ok", **self._latest_result}
        self.rep_socket.send(json.dumps(payload).encode("utf-8"))

    def run_forever(self) -> None:
        """Poll loop. Blocks until `stop()` is called (from another thread)
        or a KeyboardInterrupt is raised (Ctrl+C in the running process).

        Sockets are only ever touched by the thread running this loop --
        `stop()` just requests an exit, it doesn't close anything itself --
        since zmq sockets aren't safe to close concurrently with a poll()
        happening on another thread.
        """
        logger.info(
            "Bridge server listening: SUB=%s REP=%s",
            self.config.sub_address,
            self.config.rep_address,
        )
        try:
            while not self._stop_event.is_set():
                events = dict(self.poller.poll(timeout=1000))
                if self.sub_socket in events:
                    self._handle_frame()
                if self.rep_socket in events:
                    self._handle_request()
        except KeyboardInterrupt:
            logger.info("Shutting down")
        finally:
            self.sub_socket.close(0)
            self.rep_socket.close(0)
            self.context.term()

    def stop(self) -> None:
        """Request that `run_forever` exit (checked at most once per second).
        Call `thread.join()` after this to wait for sockets to actually close."""
        self._stop_event.set()
