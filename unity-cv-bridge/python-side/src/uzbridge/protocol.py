from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Optional

# Wire format shared by the Python and Unity (C#) sides -- keep the two in
# sync when changing anything here.
#
# Frame message (Unity PUB -> Python SUB), 3-part multipart:
#   [0] topic:  b"frame"
#   [1] header: JSON {"frame_id": int, "timestamp": float (unix epoch,
#                     sender clock), "width": int, "height": int}
#   [2] jpeg:   raw JPEG-encoded bytes
#
# Result request/reply (Unity REQ -> Python REP):
#   request: JSON {"frame_id": int | null}  (currently informational only;
#            the server always replies with its latest result)
#   reply:   JSON {"status": "ok", "frame_id": int, "timestamp": float,
#                  "results": {...}} or {"status": "no_result"}

TOPIC_FRAME = b"frame"


@dataclass
class FrameMessage:
    frame_id: int
    timestamp: float
    width: int
    height: int
    jpeg_bytes: bytes


def encode_frame(
    jpeg_bytes: bytes,
    frame_id: int,
    width: int,
    height: int,
    timestamp: Optional[float] = None,
) -> list[bytes]:
    """Build the multipart message a PUB socket should send for one frame."""
    header = {
        "frame_id": frame_id,
        "timestamp": timestamp if timestamp is not None else time.time(),
        "width": width,
        "height": height,
    }
    return [TOPIC_FRAME, json.dumps(header).encode("utf-8"), jpeg_bytes]


def decode_frame(parts: list[bytes]) -> FrameMessage:
    """Parse a multipart message received on a SUB socket."""
    if len(parts) != 3:
        raise ValueError(f"Expected 3-part frame message, got {len(parts)}")
    _topic, header_bytes, jpeg_bytes = parts
    header = json.loads(header_bytes.decode("utf-8"))
    return FrameMessage(
        frame_id=header["frame_id"],
        timestamp=header["timestamp"],
        width=header["width"],
        height=header["height"],
        jpeg_bytes=jpeg_bytes,
    )


def encode_request(frame_id: Optional[int] = None) -> bytes:
    """Build the payload a REQ client sends to ask for the latest result."""
    return json.dumps({"frame_id": frame_id}).encode("utf-8")


def decode_request(data: bytes) -> dict:
    if not data:
        return {}
    try:
        return json.loads(data.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}
