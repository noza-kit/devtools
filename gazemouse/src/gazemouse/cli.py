from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from gazemouse.calibration import CORNER_NAMES, CalibrationError, calibrate_from_corners
from gazemouse.config import load_calibration, save_calibration
from gazemouse.landmarks import LEFT_IRIS_CENTER, RIGHT_IRIS_CENTER
from gazemouse.mouse_control import PyAutoGuiMouseController
from gazemouse.screenshot import build_screenshot_fn
from gazemouse.session import GazeMouseSession, SessionConfig

app = typer.Typer(help="Hands-free gaze + gesture desktop control.")
console = Console()
err_console = Console(stderr=True)

DEFAULT_FACE_MODEL = Path.home() / ".gazemouse" / "face_landmarker.task"
DEFAULT_HAND_MODEL = Path.home() / ".gazemouse" / "hand_landmarker.task"


def _fail(message: str) -> None:
    err_console.print(f"[red]エラー: {message}[/red]")
    raise typer.Exit(code=1)


def _screen_size() -> tuple[int, int]:
    import pyautogui

    return pyautogui.size()


@app.command()
def calibrate(
    face_model: Path = typer.Option(DEFAULT_FACE_MODEL, "--face-model"),
    hand_model: Path = typer.Option(DEFAULT_HAND_MODEL, "--hand-model"),
    camera_index: int = typer.Option(0, "--camera-index"),
    output: Optional[Path] = typer.Option(None, "--output", help="Default: ~/.gazemouse/calibration.json"),
) -> None:
    """Interactive 4-corner calibration: look at each screen corner in
    turn and press Enter. Needs a real camera and the MediaPipe model
    files (see README's Install section)."""
    from gazemouse.landmarks import MediaPipeLandmarkSource

    if not face_model.exists():
        _fail(f"顔ランドマークモデルが見つかりません: {face_model}(READMEのInstallを参照)")

    screen_width, screen_height = _screen_size()
    source = MediaPipeLandmarkSource(str(face_model), str(hand_model), camera_index=camera_index)

    console.print("画面の四隅を順番に見つめて Enter を押してください。")
    corner_positions = {}
    try:
        for name in CORNER_NAMES:
            typer.prompt(f"'{name}' を見つめたら Enter", default="", show_default=False)
            frame = source.read()
            if frame is None or frame.face is None:
                _fail("顔が検出できませんでした。カメラの位置を確認してもう一度お試しください。")
            left = frame.face.points[LEFT_IRIS_CENTER]
            right = frame.face.points[RIGHT_IRIS_CENTER]
            corner_positions[name] = type(left)((left.x + right.x) / 2, (left.y + right.y) / 2)
            console.print(f"  {name}: OK")
    finally:
        source.close()

    try:
        data = calibrate_from_corners(corner_positions, screen_width, screen_height)
    except CalibrationError as e:
        _fail(str(e))

    path = save_calibration(data, output)
    console.print(f"[green]キャリブレーションを保存しました[/green] -> {path}")


@app.command()
def start(
    calibration_path: Optional[Path] = typer.Option(None, "--calibration"),
    face_model: Path = typer.Option(DEFAULT_FACE_MODEL, "--face-model"),
    hand_model: Path = typer.Option(DEFAULT_HAND_MODEL, "--hand-model"),
    camera_index: int = typer.Option(0, "--camera-index"),
    toggle_key: str = typer.Option("ctrl+alt+g", "--toggle-key", help="ON/OFF toggle hotkey"),
    target_fps: float = typer.Option(17.0, "--fps"),
) -> None:
    """Start hands-free control (Esc to panic-stop, --toggle-key to
    pause/resume, Ctrl+C in this terminal to exit entirely)."""
    from gazemouse.landmarks import MediaPipeLandmarkSource

    try:
        calibration = load_calibration(calibration_path)
    except FileNotFoundError as e:
        _fail(str(e))

    if not face_model.exists():
        _fail(f"顔ランドマークモデルが見つかりません: {face_model}(READMEのInstallを参照)")

    import keyboard

    mouse = PyAutoGuiMouseController()
    screenshot_fn = build_screenshot_fn()
    session = GazeMouseSession(mouse, calibration, config=SessionConfig(target_fps=target_fps), screenshot_fn=screenshot_fn)
    source = MediaPipeLandmarkSource(str(face_model), str(hand_model), camera_index=camera_index)

    keyboard.add_hotkey("esc", session.safety.kill_switch)
    keyboard.add_hotkey(toggle_key, session.safety.toggle)

    console.print(f"[green]開始しました[/green]。Esc で即時停止、{toggle_key} でON/OFF切替、Ctrl+C で終了。")
    try:
        while True:
            if session.should_process_frame():
                frame = source.read()
                session.process_landmarks(frame)
            else:
                time.sleep(0.001)
    except KeyboardInterrupt:
        pass
    finally:
        source.close()
        keyboard.remove_hotkey("esc")
        keyboard.remove_hotkey(toggle_key)
