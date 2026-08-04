using System;
using System.Threading;
using NetMQ;
using NetMQ.Sockets;
using UnityEngine;

namespace UzBridge
{
    /// <summary>
    /// Owns a PUB socket on a dedicated background thread and publishes
    /// whatever frame was last handed to <see cref="EnqueueFrame"/>. Capture
    /// and JPEG encoding happen on the caller's thread (Unity's texture APIs
    /// require the main thread); only the network send happens here, so a
    /// slow/blocked socket never stalls Unity's main thread.
    ///
    /// If a new frame arrives before the previous one was sent, it replaces
    /// it rather than queuing -- sending every captured frame isn't the goal,
    /// only ever sending the most recent one is.
    /// </summary>
    internal class FrameSender
    {
        private readonly string _address;
        private readonly object _lock = new object();
        private readonly AutoResetEvent _frameReady = new AutoResetEvent(false);

        private byte[] _pendingJpeg;
        private int _pendingWidth;
        private int _pendingHeight;
        private int _frameId;

        private Thread _thread;
        private volatile bool _stopRequested;

        public FrameSender(string address)
        {
            _address = address;
        }

        public void Start()
        {
            _stopRequested = false;
            _thread = new Thread(Run) { IsBackground = true, Name = "UzBridge-FrameSender" };
            _thread.Start();
        }

        public void Stop()
        {
            _stopRequested = true;
            _frameReady.Set();
            _thread?.Join(500);
        }

        public void EnqueueFrame(byte[] jpegBytes, int width, int height)
        {
            lock (_lock)
            {
                _pendingJpeg = jpegBytes;
                _pendingWidth = width;
                _pendingHeight = height;
            }
            _frameReady.Set();
        }

        private void Run()
        {
            // PUB sockets reconnect their underlying TCP connection
            // automatically (built into libzmq) when Connect() is used, so no
            // manual reconnect loop is needed here -- unlike the REQ/REP
            // result channel in ResultClient, which needs one.
            using (var socket = new PublisherSocket())
            {
                socket.Connect(_address);
                Debug.Log($"[UzBridge] FrameSender connected to {_address}");

                while (!_stopRequested)
                {
                    if (!_frameReady.WaitOne(200))
                    {
                        continue;
                    }

                    byte[] jpeg;
                    int width, height;
                    lock (_lock)
                    {
                        jpeg = _pendingJpeg;
                        width = _pendingWidth;
                        height = _pendingHeight;
                        _pendingJpeg = null;
                    }
                    if (jpeg == null) continue;

                    try
                    {
                        var message = new NetMQMessage();
                        message.Append(BridgeProtocol.TopicFrame);
                        message.Append(BridgeProtocol.BuildFrameHeaderJson(_frameId++, width, height));
                        message.Append(jpeg);
                        socket.SendMultipartMessage(message);
                    }
                    catch (Exception e)
                    {
                        Debug.LogWarning($"[UzBridge] Frame send failed: {e.Message}");
                    }
                }
            }
        }
    }
}
