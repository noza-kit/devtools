from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np
import zmq

from uzbridge import protocol
from uzbridge.config import MockConfig

logger = logging.getLogger(__name__)


class MockSender:
    """Stands in for the Unity side: publishes JPEG frames from a webcam or
    a static image file, so the bridge server can be exercised without
    Unity running."""

    def __init__(self, config: MockConfig):
        self.config = config
        self.context = zmq.Context()
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.connect(config.pub_address)
        self._frame_id = 0

    def _frame_source(self) -> Iterator[np.ndarray]:
        source = self.config.source
        if source.startswith("webcam:"):
            index = int(source.split(":", 1)[1])
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                raise RuntimeError(f"Could not open webcam index {index}")
            try:
                while True:
                    ok, frame = cap.read()
                    if not ok:
                        logger.warning("Webcam read failed, retrying")
                        continue
                    yield frame
            finally:
                cap.release()
        else:
            path = Path(source)
            image = cv2.imread(str(path))
            if image is None:
                raise RuntimeError(f"Could not read image file: {path}")
            while True:
                yield image

    def run_forever(self) -> None:
        interval = 1.0 / self.config.max_fps if self.config.max_fps > 0 else 0.0
        logger.info(
            "Mock sender publishing to %s from %s at <=%.1ffps",
            self.config.pub_address,
            self.config.source,
            self.config.max_fps,
        )
        # A PUB socket silently drops messages sent before a SUB has
        # connected and subscribed, so give the connection a moment.
        time.sleep(0.3)
        try:
            last_sent = 0.0
            for frame in self._frame_source():
                now = time.monotonic()
                wait = interval - (now - last_sent)
                if wait > 0:
                    time.sleep(wait)
                last_sent = time.monotonic()

                ok, jpeg = cv2.imencode(
                    ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.config.jpeg_quality]
                )
                if not ok:
                    logger.warning("JPEG encode failed")
                    continue

                height, width = frame.shape[:2]
                parts = protocol.encode_frame(
                    jpeg.tobytes(), frame_id=self._frame_id, width=width, height=height
                )
                self.pub_socket.send_multipart(parts)
                self._frame_id += 1
        except KeyboardInterrupt:
            logger.info("Mock sender stopped")
        finally:
            self.close()

    def close(self) -> None:
        self.pub_socket.close(0)
        self.context.term()
