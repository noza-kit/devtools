# unity-cv-bridge

Real-time video bridge between Unity and OpenCV over ZeroMQ. Unity streams
camera frames out (PUB/SUB, JPEG-compressed, rate-limited); Python processes
them with a swappable OpenCV pipeline and can send results back (REQ/REP,
JSON) for Unity to act on. Built to be reused across projects (robot arm
control, RL observations, ...), not tied to one game.

- [`python-side/`](python-side/) — pip-installable `uzbridge` package: bridge
  server, mock sender (test without Unity), pipeline framework, CLI. See
  [python-side/README.md](python-side/README.md).
- [`unity-side/`](unity-side/) — C# scripts (`UzBridgeClient` + NetMQ
  sender/receiver, Inspector config, reconnect logic). See
  [unity-side/README.md](unity-side/README.md).

## Status / progress

1. ✅ Python side implemented, unit + integration tested (19 tests).
2. ✅ Unity side implemented (`UzBridgeClient`, `FrameSender`, `ResultClient`,
   `BridgeProtocol`, sample result consumer).
3. ✅ Wire protocol verified end-to-end against a real `uzbridge serve`
   process — first via the Python mock sender (`uzbridge mock` -> `serve` ->
   `fetch`), then via a standalone .NET/NetMQ client replicating the exact
   multipart frame format and JSON field names the Unity scripts use (Unity
   Editor itself isn't installed in this dev environment, only Unity Hub).
4. ⬜ Not yet verified: compiling `unity-side/` inside an actual Unity
   Editor/project. The C# has been reviewed by hand and its wire behavior
   confirmed via the .NET client above, but Unity-specific APIs
   (`Texture2D.ReadPixels`/`EncodeToJPG`, `JsonUtility`, `MonoBehaviour`
   lifecycle) haven't run inside the real engine. Treat first-run compiler
   feedback in your project as expected, not a sign of a design problem.

## Setup

### Python side

```bash
cd python-side
pip install -e ".[dev]"
pytest              # 19 tests, ~2s
```

Try it without Unity:

```bash
# terminal 1
uzbridge serve --step contours --step color_range -v

# terminal 2 (webcam, or point --source at an image file)
uzbridge mock --source webcam:0

# terminal 3
uzbridge fetch
```

See [python-side/README.md](python-side/README.md) for the full CLI, the
wire protocol (which the Unity side must match), and how to plug in your
own OpenCV processing step.

### Unity side

1. Copy `unity-side/Assets/UzBridge/` into your Unity project's `Assets/`.
2. Install NetMQ via NuGetForUnity.
3. Add a `UzBridgeClient` component, point it at a camera/RenderTexture and
   at your running `uzbridge serve` instance.

Full steps, Inspector field reference, and how to consume results in your
own scripts: [unity-side/README.md](unity-side/README.md).

### End-to-end (Unity <-> Python)

1. `uzbridge serve --step contours --step color_range -v`
2. Press Play in Unity with a `UzBridgeClient` configured to point at the
   same host/ports.
3. Watch the Python terminal for `recv fps=... avg_latency=...ms`, and
   Unity's console for `[UzBridge] FrameSender connected to ...`.
4. Subscribe to `UzBridgeClient.OnResultReceived` (see
   `unity-side/Assets/UzBridge/Samples/ExampleResultConsumer.cs`) to react
   to detections in your scene.
