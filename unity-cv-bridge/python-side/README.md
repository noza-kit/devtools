# uzbridge

Python side of the Unity <-> OpenCV video bridge. Receives JPEG frames from
Unity over ZeroMQ, runs them through a swappable OpenCV pipeline, and serves
the results back on request. Ships with a mock sender so the whole thing can
be exercised without Unity running.

## Install

```bash
cd unity-cv-bridge/python-side
pip install -e ".[dev]"
```

## Wire protocol

See [`src/uzbridge/protocol.py`](src/uzbridge/protocol.py) for the
authoritative definitions. Summary:

- **Frames** (Unity PUB -> Python SUB), 3-part multipart message:
  `[b"frame", header JSON, JPEG bytes]`, where the header is
  `{"frame_id": int, "timestamp": float (unix epoch), "width": int, "height": int}`.
- **Results** (Unity REQ -> Python REP): Unity sends a request (currently
  just `{"frame_id": null}`, informational), Python always replies with its
  latest pipeline result:
  `{"status": "ok", "frame_id": ..., "timestamp": ..., "results": {...}}` or
  `{"status": "no_result"}` if no frame has arrived yet.

The Unity-side C# implementation must match this format exactly.

## CLI

```bash
# Start the bridge server (defaults: SUB on 5555, REP on 5556)
uzbridge serve
uzbridge serve --step contours --step color_range   # choose/order pipeline steps
uzbridge serve --sub-port 15555 --rep-port 15556 -v

# Stand in for Unity: publish frames from a webcam or a static image
uzbridge mock --source webcam:0
uzbridge mock --source ./sample.png --pub-port 15555 --max-fps 10 --jpeg-quality 70

# One-shot: fetch and print the latest result (manual REQ/REP check)
uzbridge fetch
uzbridge fetch --rep-port 15556
```

A typical local test, without Unity:

```bash
uzbridge serve --sub-port 15555 --rep-port 15556 &
uzbridge mock --pub-port 15555 --source webcam:0 &
uzbridge fetch --rep-port 15556
```

## Pipeline: swapping in your own processing

A `Pipeline` is an ordered list of functions with signature
`(frame: np.ndarray, context: dict) -> dict`. Each step's return value is
merged into `context` under its own name, so later steps can build on
earlier ones (e.g. reuse a grayscale conversion).

```python
from uzbridge.pipeline import Pipeline

def my_step(frame, context):
    # ... cv2 processing ...
    return {"label": "cup", "confidence": 0.92}

pipeline = Pipeline().add_step(my_step, name="detector")
results = pipeline.process(frame)  # {"detector": {"label": "cup", "confidence": 0.92}}
```

Two example steps ship in `uzbridge.ops` and are wired into the `serve`
CLI's `--step` flag:

| Step | Returns | Notes |
| --- | --- | --- |
| `contours` (`uzbridge.ops.contour_detect`) | `{"count": int, "boxes": [{"x","y","width","height","area"}, ...]}` | Canny edges + `findContours`, filtered by `min_area` |
| `color_range` (`uzbridge.ops.color_range`) | `{"found": bool, "cx", "cy", "area"}` | Largest blob in an HSV range; defaults to yellow-green |

To add your own (object detection, a trained model, whatever): write a
function with the same signature, register it in `uzbridge.cli.STEPS`, and
pass `--step your_name` to `serve`.

## FPS / latency logging

`BridgeServer` logs `recv fps=... avg_latency=...ms` every `--log-interval`
seconds (default 5s). Latency is measured against the `timestamp` the
sender embedded in the frame header, so it reflects Unity-capture-to-Python-
processed time, not just network transit -- keep the sender and receiver
clocks reasonably in sync (both `uzbridge mock` and the Unity side should
use wall-clock `time.time()` / `DateTimeOffset.UtcNow` equivalents).

## Library

```python
import cv2
from uzbridge import BridgeServer, MockSender, Pipeline, ServerConfig, MockConfig
from uzbridge.ops import contour_detect

pipeline = Pipeline().add_step(contour_detect, name="contours")
server = BridgeServer(ServerConfig(sub_port=5555, rep_port=5556), pipeline)
server.run_forever()  # blocks; Ctrl+C or call server.stop() from another thread
```

## Development

```bash
pip install -e ".[dev]"
pytest
```
