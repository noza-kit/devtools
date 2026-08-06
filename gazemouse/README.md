# gazemouse

Hands-free desktop control: eye tracking moves the mouse cursor, and a
set of deliberate gestures (never just "looking") drive every action —
a right-hand fist for clicking/dragging, a sustained 2-second eye
closure for a screenshot (via [`snapclip`](../snapclip)), and a head
tilt for scrolling. "Just looking" never triggers anything by itself
(the classic Midas-touch problem eye-tracking UIs have to solve) —
only pointer movement is gaze-driven; every action is gated behind its
own distinct gesture.

**Windows only. Needs a webcam.** See [Known limitations](#known-limitations)
for what in this implementation has and hasn't been verified against
real hardware.

- [Install](#install)
- [Calibration](#calibration)
- [`gazemouse start`](#gazemouse-start)
- [Gesture reference](#gesture-reference)
- [Safety / fail-safes](#safety--fail-safes)
- [Architecture](#architecture)
- [Known limitations](#known-limitations)
- [Development](#development)

## Install

```bash
cd gazemouse
pip install -e ".[dev]"
```

`gazemouse start`/`calibrate` additionally need two MediaPipe **Tasks
API** model bundles (MediaPipe 1.x removed the older `mp.solutions.*`
API this project's original reference materials were written against —
this implementation targets the current Tasks API,
`mediapipe.tasks.python.vision.FaceLandmarker`/`HandLandmarker`,
instead) downloaded once, by hand:

1. [Face landmarker model](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker#models)
   — download `face_landmarker.task` and save it to
   `~/.gazemouse/face_landmarker.task` (or pass `--face-model
   path/to/file.task` on every command instead).
2. [Hand landmarker model](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker#models)
   — same idea, `hand_landmarker.task` ->
   `~/.gazemouse/hand_landmarker.task` (or `--hand-model`).

Optional but recommended: install [`snapclip`](../snapclip) too, so the
2-second-blink screenshot gesture actually does something —
`gazemouse` imports `snapclip.capture` directly if it's installed, and
simply disables that one gesture (logging a warning once, not an
error) if it isn't.

```bash
pip install -e "../snapclip"   # optional: enables blink-triggered screenshots
```

## Calibration

```bash
gazemouse calibrate
```

Prompts you to look at each of the 4 screen corners in turn and press
Enter; records your iris position at each corner via the camera, and
saves the resulting mapping to `~/.gazemouse/calibration.json`
(`--output` for a different path). Re-run this any time lighting,
camera position, or seating position changes significantly — gaze
mapping is a simple linear fit between "iris position observed at each
corner" and "that corner's screen coordinate," so it degrades along
with how representative those 4 reference points still are.

## `gazemouse start`

```bash
gazemouse start
gazemouse start --calibration ./my-calibration.json
gazemouse start --toggle-key "ctrl+alt+g"   # default
gazemouse start --fps 15
```

Runs the full hands-free control loop in the foreground until Ctrl+C
(in the terminal it was started from) or a fatal error. See
[Safety](#safety--fail-safes) for how to pause/stop it without
touching the keyboard focus of whatever app you're using.

## Gesture reference

| You do | Detected via | Result |
| --- | --- | --- |
| Look somewhere on screen | Iris position (both eyes' `FaceLandmarker` iris landmarks, averaged), EMA-smoothed | Cursor glides there — pointer-only, never triggers an action by itself |
| Close your right hand into a fist | `HandLandmarker`, open/closed by finger-tip-vs-knuckle distance | Mouse button **down** (the open->closed transition) |
| Open your hand again | Same | Mouse button **up** — a quick close+open is a click; staying closed while looking elsewhere is a drag, for free, since it's the same down/up mechanism a physical mouse button uses |
| Close both eyes (or just one — a deliberate wink also counts) for a sustained **2 seconds** | Eye Aspect Ratio (EAR) on both eyes, the *lower* of the two checked against the hold timer | One screenshot, via `snapclip`'s own stack-capture logic (same save location/Markdown-or-LaTeX markup snapclip itself uses) |
| Tilt your head up/down | Chin-to-forehead vertical distance in the face mesh, relative to a per-session baseline | Scroll up/down — deliberately *not* tied to gaze, so looking down to read further down a page doesn't also drag the cursor down (the exact "コントロールとビューの競合" the original spec calls out) |

## Safety / fail-safes

- **Esc** immediately force-disables gazemouse (the "kill switch") —
  this does *not* self-re-enable just because your face comes back
  into frame; you chose to turn it off.
- **`--toggle-key`** (default `Ctrl+Alt+G`) explicitly flips
  enabled/disabled, for a deliberate pause/resume distinct from Esc's
  always-off panic button.
- **Losing your face from frame** (camera blocked, you stood up and
  walked away) automatically disables cursor/gesture control until
  your face is detected again — this one *does* self-recover, since
  nothing was deliberately turned off.
- **Frame-rate limiting**: landmark detection/inference only runs at
  `--fps` (default 17, within the spec's 15-20fps budget) even if the
  camera itself produces frames faster, capping CPU/GPU load.
- Independently of all of the above, the underlying
  [`pyautogui`](https://pyautogui.readthedocs.io/) mouse-control layer
  keeps its own built-in corner fail-safe active (forcing the cursor
  into a physical screen corner aborts whatever pyautogui call is in
  flight) as a second, unrelated safety net.

## Architecture

| Module | Responsibility |
| --- | --- |
| `landmarks.py` | Plain `Point`/`FaceLandmarks`/`HandLandmarks` types + a `LandmarkSource` protocol; `MediaPipeLandmarkSource` is the real webcam+Tasks-API backend |
| `gaze.py` | `EmaSmoother` — exponential moving average cursor smoothing |
| `calibration.py` | 4-corner calibration -> iris-position bounding box -> linear (clamped) screen-coordinate mapping |
| `blink.py` | Eye Aspect Ratio (EAR) + `BlinkDetector`, a sustained-2-second-closure state machine |
| `handgesture.py` | Open/closed hand detection + `ClickGestureDetector` (open<->closed edges -> mouse press/release) |
| `headtilt.py` | Head-pitch proxy (chin-to-forehead distance) + `HeadTiltScroll` (baseline-relative, deadzoned) |
| `safety.py` | `SafetyMonitor` — face-visibility + kill-switch + toggle, combined into one `is_active` flag |
| `mouse_control.py` | `MouseController` protocol; `PyAutoGuiMouseController` is the real OS backend |
| `screenshot.py` | Soft-optional `snapclip` integration for the blink gesture |
| `session.py` | `GazeMouseSession` — the per-frame pipeline tying all of the above together, plus FPS limiting |
| `config.py` | Calibration data persistence (`~/.gazemouse/calibration.json`) |
| `cli.py` | Typer CLI: `calibrate`, `start` |

`GazeMouseSession.process_landmarks()` takes plain `FrameLandmarks` and
drives a `MouseController` — neither MediaPipe nor pyautogui are
referenced by name anywhere in that decision logic, which is what
makes the whole pipeline (gaze mapping, click/drag edges, blink
timing, head-tilt scroll, safety gating, and their interactions) fully
unit-testable with synthetic landmark data and a fake mouse, with no
camera or real MediaPipe inference involved.

## Known limitations

**This implementation could not be verified against a real camera,
real face, or real hand in this environment** (no camera available;
even with one, the MediaPipe Tasks API additionally needs the model
files downloaded per [Install](#install), which wasn't done here
either). Concretely, what that means:

- The exact **landmark indices** used for the iris center, the 6 EAR
  eye-outline points, and the finger tip/PIP joints
  (`landmarks.py`'s constants) are the standard indices widely
  documented and used across the MediaPipe community for exactly
  these purposes, not independently re-derived or verified against a
  real face here.
- The **open/closed hand heuristic** (tip-farther-than-PIP-from-wrist,
  majority of 4 fingers) and the **EAR closed-eye threshold**
  (`0.2`, a commonly-cited default in blink-detection literature) are
  reasonable starting points, not tuned against real footage — expect
  to adjust `SessionConfig.ear_threshold` and/or revisit
  `handgesture.is_hand_open`'s threshold once you can test with a real
  camera.
- The **calibration flow, gaze mapping, EMA smoothing, blink timing,
  click/drag edge detection, head-tilt scroll, and safety gating** are
  all fully exercised by the automated test suite using synthetic
  landmark data (see [Development](#development)) — that algorithmic
  layer is verified logic, just not yet verified *against a real human
  face and hand*.
- `MediaPipeLandmarkSource` (the real camera+model backend) is
  structurally checked against the installed MediaPipe Tasks API's
  actual method signatures (confirmed to match during development),
  but never actually invoked end-to-end.

Manually verifying the above — running `gazemouse calibrate` then
`gazemouse start` against your own face/hand/head and adjusting
`SessionConfig`'s thresholds to taste — is the natural next step once
you have a webcam and the model files in place.

## Development

```bash
pip install -e ".[dev]"
pytest
```

Real, no mocking: every pure-logic module (`gaze`, `calibration`,
`blink`, `handgesture`, `headtilt`, `safety`) and their integration in
`session.py`, driven by synthetic `FaceLandmarks`/`HandLandmarks`
fixtures (`tests/conftest.py`'s `face_factory`/`hand_factory`) and a
fake in-memory `MouseController` that records every call. Not
exercised (see [Known limitations](#known-limitations) for why):
`MediaPipeLandmarkSource`'s real camera/inference calls,
`PyAutoGuiMouseController`'s real OS mouse control, and `cli.py`'s
`calibrate`/`start` command bodies beyond their config-validation error
paths (missing calibration file, missing model file).
