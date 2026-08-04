using System;
using System.Collections;
using System.Collections.Concurrent;
using UnityEngine;

namespace UzBridge
{
    /// <summary>
    /// Streams a camera/RenderTexture out to a Python OpenCV pipeline over
    /// ZeroMQ (JPEG frames via PUB/SUB) and receives its processed results
    /// back (JSON via REQ/REP). Drop this on a GameObject, point it at a
    /// camera or RenderTexture, and subscribe to <see cref="OnResultReceived"/>
    /// to react to whatever the Python side detects.
    /// </summary>
    public class UzBridgeClient : MonoBehaviour
    {
        [Header("Connection")]
        [Tooltip("Host running the Python uzbridge server.")]
        [SerializeField] private string serverAddress = "localhost";
        [Tooltip("Python server's SUB port -- frames are published here.")]
        [SerializeField] private int framePubPort = 5555;
        [Tooltip("Python server's REP port -- results are requested here.")]
        [SerializeField] private int resultReqPort = 5556;

        [Header("Video Source")]
        [Tooltip("Captured directly if set. Leave empty to capture from Source Camera instead.")]
        [SerializeField] private RenderTexture sourceRenderTexture;
        [Tooltip("Used when Source Render Texture is empty: rendered into an internally-managed RenderTexture each capture.")]
        [SerializeField] private Camera sourceCamera;

        [Header("Send Settings")]
        [Tooltip("Maximum frames sent per second.")]
        [SerializeField] private float sendFps = 15f;
        [Range(1, 100)]
        [Tooltip("JPEG compression quality (higher = larger, better quality).")]
        [SerializeField] private int jpegQuality = 80;

        [Header("Result Polling")]
        [Tooltip("Seconds between requests for the latest result.")]
        [SerializeField] private float resultPollIntervalSeconds = 0.2f;
        [Tooltip("Seconds to wait for a reply before treating the request as failed and reconnecting.")]
        [SerializeField] private float resultTimeoutSeconds = 1f;

        /// <summary>Fired on the main thread whenever a new result is received.</summary>
        public event Action<BridgeResult> OnResultReceived;

        private FrameSender _frameSender;
        private ResultClient _resultClient;
        private Texture2D _captureTexture;
        private RenderTexture _internalCameraTexture;
        private Coroutine _captureCoroutine;
        private readonly ConcurrentQueue<BridgeResult> _mainThreadResults = new ConcurrentQueue<BridgeResult>();

        private void OnEnable()
        {
            NetMqCleanup.EnsureInitialized();

            _frameSender = new FrameSender($"tcp://{serverAddress}:{framePubPort}");
            _frameSender.Start();

            _resultClient = new ResultClient(
                $"tcp://{serverAddress}:{resultReqPort}",
                resultPollIntervalSeconds,
                resultTimeoutSeconds);
            _resultClient.ResultReceived += result => _mainThreadResults.Enqueue(result);
            _resultClient.Start();

            _captureCoroutine = StartCoroutine(CaptureLoop());
        }

        private void OnDisable()
        {
            if (_captureCoroutine != null)
            {
                StopCoroutine(_captureCoroutine);
                _captureCoroutine = null;
            }

            _frameSender?.Stop();
            _resultClient?.Stop();

            if (_captureTexture != null)
            {
                Destroy(_captureTexture);
                _captureTexture = null;
            }
            if (_internalCameraTexture != null)
            {
                _internalCameraTexture.Release();
                Destroy(_internalCameraTexture);
                _internalCameraTexture = null;
            }
        }

        private void Update()
        {
            while (_mainThreadResults.TryDequeue(out var result))
            {
                OnResultReceived?.Invoke(result);
            }
        }

        private IEnumerator CaptureLoop()
        {
            while (true)
            {
                CaptureAndSend();
                float interval = sendFps > 0f ? 1f / sendFps : 0f;
                yield return interval > 0f ? new WaitForSeconds(interval) : null;
            }
        }

        private void CaptureAndSend()
        {
            RenderTexture rt = ResolveSourceTexture();
            if (rt == null) return;

            if (_captureTexture == null || _captureTexture.width != rt.width || _captureTexture.height != rt.height)
            {
                if (_captureTexture != null) Destroy(_captureTexture);
                _captureTexture = new Texture2D(rt.width, rt.height, TextureFormat.RGB24, false);
            }

            RenderTexture previous = RenderTexture.active;
            RenderTexture.active = rt;
            _captureTexture.ReadPixels(new Rect(0, 0, rt.width, rt.height), 0, 0);
            _captureTexture.Apply(false);
            RenderTexture.active = previous;

            byte[] jpeg = _captureTexture.EncodeToJPG(jpegQuality);
            _frameSender.EnqueueFrame(jpeg, rt.width, rt.height);
        }

        private RenderTexture ResolveSourceTexture()
        {
            if (sourceRenderTexture != null)
            {
                return sourceRenderTexture;
            }
            if (sourceCamera == null)
            {
                return null;
            }

            int width = Mathf.Max(1, sourceCamera.pixelWidth);
            int height = Mathf.Max(1, sourceCamera.pixelHeight);
            if (_internalCameraTexture == null || _internalCameraTexture.width != width || _internalCameraTexture.height != height)
            {
                if (_internalCameraTexture != null)
                {
                    _internalCameraTexture.Release();
                    Destroy(_internalCameraTexture);
                }
                _internalCameraTexture = new RenderTexture(width, height, 24);
            }

            RenderTexture previousTarget = sourceCamera.targetTexture;
            sourceCamera.targetTexture = _internalCameraTexture;
            sourceCamera.Render();
            sourceCamera.targetTexture = previousTarget;

            return _internalCameraTexture;
        }
    }
}
