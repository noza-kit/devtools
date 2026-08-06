from __future__ import annotations


class SafetyMonitor:
    """The two required fail-safes: losing the face from frame (camera
    blocked, user walked away) and an explicit kill switch (Esc key, or
    the ON/OFF toggle hotkey). Either forces `is_active` false. Losing
    and regaining the face re-activates automatically (nothing was
    deliberately turned off); the kill switch does not -- it needs an
    explicit re_enable(), since the user chose to turn gazemouse off
    and getting their face back in frame shouldn't silently override
    that."""

    def __init__(self):
        self._enabled = True
        self._face_visible = True

    def update_face_visibility(self, face_detected: bool) -> None:
        self._face_visible = face_detected

    def kill_switch(self) -> None:
        self._enabled = False

    def re_enable(self) -> None:
        self._enabled = True

    def toggle(self) -> bool:
        """Flips the explicit enabled/disabled state (the ON/OFF toggle
        hotkey, distinct from Esc's always-off kill switch). Returns
        the new `_enabled` state."""
        self._enabled = not self._enabled
        return self._enabled

    @property
    def is_active(self) -> bool:
        return self._enabled and self._face_visible
