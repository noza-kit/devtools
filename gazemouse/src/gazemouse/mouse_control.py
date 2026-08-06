from __future__ import annotations

from typing import Protocol


class MouseController(Protocol):
    def move_to(self, x: int, y: int) -> None: ...
    def mouse_down(self) -> None: ...
    def mouse_up(self) -> None: ...
    def scroll(self, amount: int) -> None: ...


class PyAutoGuiMouseController:
    """Real OS mouse control via pyautogui. `_pause=False` on every call
    disables pyautogui's default 0.1s post-call sleep (meant for
    scripted automation, not a 15-20fps real-time control loop) --
    pyautogui's corner fail-safe (abort if the cursor is forced into a
    screen corner) is left on as a second, independent panic button
    alongside gazemouse's own Esc/toggle kill switch."""

    def move_to(self, x: int, y: int) -> None:
        import pyautogui

        pyautogui.moveTo(x, y, _pause=False)

    def mouse_down(self) -> None:
        import pyautogui

        pyautogui.mouseDown(_pause=False)

    def mouse_up(self) -> None:
        import pyautogui

        pyautogui.mouseUp(_pause=False)

    def scroll(self, amount: int) -> None:
        import pyautogui

        pyautogui.scroll(amount, _pause=False)
