using System;
using System.Threading;
using NetMQ;
using NetMQ.Sockets;
using UnityEngine;

namespace UzBridge
{
    /// <summary>
    /// Owns a REQ socket on a dedicated background thread and repeatedly asks
    /// the Python server for its latest pipeline result.
    ///
    /// Unlike PUB/SUB, ZMQ's REQ/REP state machine can't recover on its own
    /// from a request that never gets a reply (e.g. the Python server
    /// restarted mid-request): the socket is left permanently expecting a
    /// reply that will never arrive. So on a timeout, the socket is closed
    /// and a fresh one created and reconnected before the next attempt --
    /// the "Lazy Pirate" pattern from the ZeroMQ guide.
    /// </summary>
    internal class ResultClient
    {
        private readonly string _address;
        private readonly int _pollIntervalMs;
        private readonly int _timeoutMs;

        private Thread _thread;
        private volatile bool _stopRequested;

        /// <summary>Fired from the background thread -- marshal to the main
        /// thread before touching any Unity object.</summary>
        public event Action<BridgeResult> ResultReceived;

        public ResultClient(string address, float pollIntervalSeconds, float timeoutSeconds)
        {
            _address = address;
            _pollIntervalMs = Mathf.Max(0, Mathf.RoundToInt(pollIntervalSeconds * 1000f));
            _timeoutMs = Mathf.Max(100, Mathf.RoundToInt(timeoutSeconds * 1000f));
        }

        public void Start()
        {
            _stopRequested = false;
            _thread = new Thread(Run) { IsBackground = true, Name = "UzBridge-ResultClient" };
            _thread.Start();
        }

        public void Stop()
        {
            _stopRequested = true;
            _thread?.Join(_timeoutMs + 500);
        }

        private void Run()
        {
            RequestSocket socket = CreateSocket();

            while (!_stopRequested)
            {
                try
                {
                    socket.SendFrame(BridgeProtocol.BuildRequestJson());
                    if (socket.TryReceiveFrameString(TimeSpan.FromMilliseconds(_timeoutMs), out string reply))
                    {
                        if (BridgeProtocol.TryDecodeResult(reply, out var envelope, out var resultsJson))
                        {
                            ResultReceived?.Invoke(new BridgeResult
                            {
                                Success = envelope.status == "ok",
                                Status = envelope.status,
                                FrameId = envelope.frame_id,
                                Timestamp = envelope.timestamp,
                                ResultsJson = resultsJson,
                            });
                        }
                    }
                    else
                    {
                        Debug.LogWarning("[UzBridge] Result request timed out, reconnecting");
                        socket.Dispose();
                        socket = CreateSocket();
                    }
                }
                catch (Exception e)
                {
                    Debug.LogWarning($"[UzBridge] Result client error, reconnecting: {e.Message}");
                    socket.Dispose();
                    socket = CreateSocket();
                }

                if (!_stopRequested && _pollIntervalMs > 0)
                {
                    Thread.Sleep(_pollIntervalMs);
                }
            }

            socket.Dispose();
        }

        private RequestSocket CreateSocket()
        {
            var socket = new RequestSocket();
            socket.Connect(_address);
            return socket;
        }
    }
}
