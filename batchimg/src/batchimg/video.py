from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2

from batchimg.resize import compute_target_size, resize_image


class VideoReadError(Exception):
    pass


def process_video(
    source: Path,
    destination: Path,
    *,
    target_size: Optional[tuple[int, int]] = None,
    keep_aspect: bool = True,
    trim_start: Optional[float] = None,
    trim_end: Optional[float] = None,
) -> int:
    """Resize and/or trim a video, writing the result to `destination`.

    `trim_start`/`trim_end` are seconds. Returns the number of frames written.
    """
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise VideoReadError(f"Could not open video: {source}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if target_size:
            out_w, out_h = compute_target_size(orig_w, orig_h, *target_size, keep_aspect)
        else:
            out_w, out_h = orig_w, orig_h

        start_frame = int(trim_start * fps) if trim_start else 0
        end_frame = int(trim_end * fps) if trim_end is not None else None
        if start_frame:
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        destination.parent.mkdir(parents=True, exist_ok=True)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(destination), fourcc, fps, (out_w, out_h))
        try:
            frame_index = start_frame
            written = 0
            while end_frame is None or frame_index < end_frame:
                ok, frame = cap.read()
                if not ok:
                    break
                if target_size:
                    frame = resize_image(frame, *target_size, keep_aspect)
                writer.write(frame)
                written += 1
                frame_index += 1
        finally:
            writer.release()
    finally:
        cap.release()

    if written == 0:
        destination.unlink(missing_ok=True)
        raise VideoReadError(f"No frames written for {source} (check trim range)")

    return written
