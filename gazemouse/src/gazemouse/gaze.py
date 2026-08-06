from __future__ import annotations

from typing import Optional


class EmaSmoother:
    """Exponential moving average: Smooth = alpha*Current + (1-alpha)*Previous.
    Damps the iris's natural micro-jitter into a cursor that glides
    rather than shakes. Higher `alpha` tracks the raw input more
    closely (less lag, more jitter); lower `alpha` is smoother but
    laggier."""

    def __init__(self, alpha: float = 0.3):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self._prev: Optional[tuple[float, float]] = None

    def smooth(self, x: float, y: float) -> tuple[float, float]:
        if self._prev is None:
            self._prev = (x, y)
            return self._prev
        prev_x, prev_y = self._prev
        smoothed = (
            self.alpha * x + (1 - self.alpha) * prev_x,
            self.alpha * y + (1 - self.alpha) * prev_y,
        )
        self._prev = smoothed
        return smoothed

    def reset(self) -> None:
        self._prev = None
