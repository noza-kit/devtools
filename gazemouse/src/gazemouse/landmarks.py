from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, Sequence

# Standard MediaPipe Face Mesh (478-point, iris-refined) landmark indices,
# as commonly used across the MediaPipe community for exactly these
# purposes -- not independently re-derived here, since that would need a
# real camera + face to verify against (see README's "Known limitations").
LEFT_IRIS_CENTER = 468
RIGHT_IRIS_CENTER = 473
# (outer_corner, upper_1, upper_2, inner_corner, lower_1, lower_2), the six
# points the standard EAR (Eye Aspect Ratio) formula is defined over.
LEFT_EYE_EAR_INDICES = (33, 160, 158, 133, 153, 144)
RIGHT_EYE_EAR_INDICES = (263, 387, 385, 362, 380, 373)
FOREHEAD_INDEX = 10
CHIN_INDEX = 152

# Standard MediaPipe Hands (21-point) landmark indices.
WRIST_INDEX = 0
FINGER_TIP_INDICES = (8, 12, 16, 20)  # index, middle, ring, pinky
FINGER_PIP_INDICES = (6, 10, 14, 18)  # each finger's middle joint


@dataclass(frozen=True)
class Point:
    x: float  # normalized [0, 1] image coordinates (MediaPipe's own convention)
    y: float
    z: float = 0.0


@dataclass(frozen=True)
class FaceLandmarks:
    points: Sequence[Point]  # indexed per the constants above


@dataclass(frozen=True)
class HandLandmarks:
    points: Sequence[Point]


@dataclass(frozen=True)
class FrameLandmarks:
    face: Optional[FaceLandmarks] = None
    hand: Optional[HandLandmarks] = None


class LandmarkSource(Protocol):
    def read(self) -> Optional[FrameLandmarks]:
        """Capture one frame and return whatever landmarks were detected
        in it (either field may be None if that feature wasn't
        detected this frame), or None entirely if no frame could be
        read at all (e.g. camera disconnected)."""
        ...


class MediaPipeLandmarkSource:
    """Real webcam + MediaPipe Tasks API (FaceLandmarker + HandLandmarker)
    backend. MediaPipe 1.x's Tasks API needs separately-downloaded
    `.task` model bundles (`face_landmarker.task` and
    `hand_landmarker.task`) -- see README's Install section. Not
    exercised by the automated test suite (needs a real camera + these
    model files); the rest of the pipeline consumes plain
    FrameLandmarks and is tested independently via a fake
    LandmarkSource."""

    def __init__(self, face_model_path: str, hand_model_path: str, camera_index: int = 0):
        import cv2
        from mediapipe.tasks.python import BaseOptions, vision

        self._face_landmarker = vision.FaceLandmarker.create_from_options(
            vision.FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=face_model_path),
                num_faces=1,
            )
        )
        self._hand_landmarker = vision.HandLandmarker.create_from_options(
            vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=hand_model_path),
                num_hands=1,
            )
        )
        self._capture = cv2.VideoCapture(camera_index)

    def read(self) -> Optional[FrameLandmarks]:
        import mediapipe as mp

        ok, frame = self._capture.read()
        if not ok:
            return None

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
        face_result = self._face_landmarker.detect(mp_image)
        hand_result = self._hand_landmarker.detect(mp_image)

        face = None
        if face_result.face_landmarks:
            face = FaceLandmarks(
                points=[Point(p.x, p.y, p.z) for p in face_result.face_landmarks[0]]
            )

        hand = None
        if hand_result.hand_landmarks:
            hand = HandLandmarks(
                points=[Point(p.x, p.y, p.z) for p in hand_result.hand_landmarks[0]]
            )

        return FrameLandmarks(face=face, hand=hand)

    def close(self) -> None:
        self._capture.release()
