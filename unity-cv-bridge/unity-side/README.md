# unity-side (UzBridge)

C# scripts that stream a Unity camera/RenderTexture to the `uzbridge` Python
server over ZeroMQ and receive its processed results back. Designed to be
copied (or symlinked) as a self-contained folder into any Unity project's
`Assets/`.

## Requirements

- Unity 2020.3 LTS or newer (uses `RenderTexture`/`Texture2D` APIs and C#
  language features available since then; older versions likely work too
  but are untested).
- [NetMQ](https://github.com/zeromq/netmq) (+ its `AsyncIO` dependency), not
  included here -- see install steps below.

## Install

1. Copy `unity-side/Assets/UzBridge/` into your Unity project's `Assets/`
   folder (or symlink it, so updates here stay in sync).
2. Install NetMQ via [NuGetForUnity](https://github.com/GlitchEnzo/NuGetForUnity):
   - Add NuGetForUnity to your project (Package Manager -> "Install package
     from git URL" -> `https://github.com/GlitchEnzo/NuGetForUnity.git?path=/src/NuGetForUnity`,
     or follow that repo's current install instructions).
   - Open **NuGet -> Manage NuGet Packages**, search for `NetMQ`, install
     the latest version. This pulls in `AsyncIO` automatically.
3. Back in Unity, let it finish compiling. `UzBridge.Runtime.asmdef`
   doesn't list NetMQ as an explicit assembly reference (NuGetForUnity's
   output setup varies by version), so if you get "type or namespace NetMQ
   could not be found":
   - Check whether NuGetForUnity generated its own `.asmdef` for the NetMQ
     DLL (recent versions do, under `Assets/Packages/NetMQ.*`); if so, open
     `Assets/UzBridge/Runtime/UzBridge.Runtime.asmdef` in the Inspector and
     add that assembly under **Assembly Definition References**.
     - If NetMQ is a plain `.dll` plugin with no asmdef of its own, it's
       automatically visible to every asmdef and no change is needed.
4. Confirm `NetMQ.dll` targets .NET Standard 2.0/2.1 in its plugin importer
   settings if you hit platform-specific compile errors (NuGetForUnity
   usually gets this right automatically).

## Setup in a scene

1. Add a `UzBridgeClient` component to any GameObject.
2. Set **Server Address** / **Frame Pub Port** / **Result Req Port** to
   match wherever `uzbridge serve` is running (defaults: `localhost`,
   `5555`, `5556`).
3. Set **Source Render Texture** (if something already renders into one) or
   **Source Camera** (it'll be rendered into an internally-managed
   RenderTexture each capture).
4. Tune **Send Fps** and **Jpeg Quality** to taste (defaults: 15fps, 80).
5. Press Play. With `uzbridge serve` running, you should see log lines like
   `[UzBridge] FrameSender connected to tcp://localhost:5555` and, on the
   Python side, `recv fps=... avg_latency=...ms`.

## Inspector reference

| Field | Default | Notes |
| --- | --- | --- |
| Server Address | `localhost` | Host running `uzbridge serve` |
| Frame Pub Port | `5555` | Must match the server's `--sub-port` |
| Result Req Port | `5556` | Must match the server's `--rep-port` |
| Source Render Texture | _(none)_ | Captured directly if set |
| Source Camera | _(none)_ | Used only when Source Render Texture is empty |
| Send Fps | `15` | Frames captured+sent per second, `0` = uncapped |
| Jpeg Quality | `80` | 1-100, passed to `Texture2D.EncodeToJPG` |
| Result Poll Interval Seconds | `0.2` | How often to ask Python for the latest result |
| Result Timeout Seconds | `1.0` | Reconnects the REQ socket if a reply doesn't arrive in time |

## Receiving results

Subscribe to `UzBridgeClient.OnResultReceived` (fired on the main thread,
safe to touch other Unity objects from):

```csharp
[SerializeField] private UzBridgeClient bridge;

void OnEnable() => bridge.OnResultReceived += HandleResult;
void OnDisable() => bridge.OnResultReceived -= HandleResult;

void HandleResult(BridgeResult result)
{
    if (!result.Success) return;
    // result.ResultsJson is the raw JSON of the pipeline's "results" object
    // -- its shape depends on which steps you registered on the Python
    // side (`uzbridge serve --step ...`). Parse it with your own
    // [Serializable] class via JsonUtility.FromJson.
}
```

See [`Samples/ExampleResultConsumer.cs`](Assets/UzBridge/Samples/ExampleResultConsumer.cs)
for a working example that tracks a `Transform` from the `color_range`
step's output.

## Architecture notes

- `FrameSender` and `ResultClient` each own their ZeroMQ socket on a
  dedicated background thread -- sockets aren't safe to share across
  threads, and capture (`ReadPixels`/`EncodeToJPG`) must stay on the main
  thread, so only the actual network I/O is offloaded.
- Only the *latest* captured frame is ever sent (a newer frame overwrites a
  still-unsent older one) -- this avoids a growing backlog if the network
  or Python-side processing is briefly slower than the capture rate.
- PUB/SUB (frame sending) reconnects automatically -- that's inherent to
  ZeroMQ's TCP transport. REQ/REP (result fetching) does not recover on its
  own from a dropped reply (a ZeroMQ REQ/REP quirk), so `ResultClient`
  detects a timeout and recreates the socket itself (the "Lazy Pirate"
  pattern).
- `NetMqCleanup` handles the `AsyncIO.ForceDotNet.Force()` /
  `NetMQConfig.Cleanup()` calls NetMQ needs under Unity to avoid hangs on
  Play-mode stop / build quit.

## Known limitation

This code hasn't been compiled inside the Unity Editor in this environment
(no Unity Editor install available here, only Unity Hub) -- it's been
reviewed by hand against the NetMQ/UnityEngine APIs it calls, but if the
compiler surfaces something once you open it in your project, treat that as
expected first-run friction, not a sign the design is wrong.
