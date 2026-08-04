using System;
using UnityEngine;

namespace UzBridge
{
    /// <summary>
    /// Wire format shared with the Python side (python-side/src/uzbridge/protocol.py).
    /// Keep the two in sync when changing anything here.
    ///
    /// Frame message (this side PUB -> Python SUB), 3-part multipart:
    ///   [0] topic:  "frame"
    ///   [1] header: JSON {"frame_id", "timestamp" (unix epoch seconds), "width", "height"}
    ///   [2] jpeg:   raw JPEG-encoded bytes
    ///
    /// Result request/reply (this side REQ -> Python REP):
    ///   request: JSON {"frame_id": int|null}
    ///   reply:   JSON {"status": "ok", "frame_id", "timestamp", "results": {...}}
    ///            or {"status": "no_result"}
    /// </summary>
    public static class BridgeProtocol
    {
        public const string TopicFrame = "frame";

        // Field names must match the JSON keys exactly -- JsonUtility maps by
        // field name only, it doesn't support per-field renaming.
        [Serializable]
        public class FrameHeader
        {
            public int frame_id;
            public double timestamp;
            public int width;
            public int height;
        }

        [Serializable]
        public class ResultEnvelope
        {
            public string status;
            public int frame_id;
            public double timestamp;
            // "results" is intentionally not a field here: its shape depends on
            // which pipeline steps are registered on the Python side, and
            // JsonUtility can't deserialize a dynamically-shaped object. It's
            // extracted separately as raw JSON text by TryDecodeResult below.
        }

        public static double UnixTimeNow()
        {
            return DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0;
        }

        public static string BuildFrameHeaderJson(int frameId, int width, int height, double? timestamp = null)
        {
            var header = new FrameHeader
            {
                frame_id = frameId,
                timestamp = timestamp ?? UnixTimeNow(),
                width = width,
                height = height,
            };
            return JsonUtility.ToJson(header);
        }

        public static string BuildRequestJson(int? frameId = null)
        {
            // The server currently ignores the request body and always replies
            // with its latest result; frame_id is included for future filtering.
            return frameId.HasValue ? $"{{\"frame_id\":{frameId.Value}}}" : "{\"frame_id\":null}";
        }

        public static bool TryDecodeResult(string json, out ResultEnvelope envelope, out string resultsJson)
        {
            envelope = null;
            resultsJson = null;

            if (string.IsNullOrEmpty(json))
            {
                return false;
            }

            try
            {
                envelope = JsonUtility.FromJson<ResultEnvelope>(json);
            }
            catch (ArgumentException)
            {
                return false;
            }

            if (envelope == null || string.IsNullOrEmpty(envelope.status))
            {
                return false;
            }

            resultsJson = ExtractRawObject(json, "results");
            return true;
        }

        /// <summary>
        /// Extracts the raw JSON text of a top-level "key": {...} object by
        /// brace-counting, without parsing the rest of the document. Used
        /// instead of a full JSON library so the pipeline's dynamically-shaped
        /// "results" object can be handed to callers as-is, for them to parse
        /// with whatever they defined their own step result classes as.
        /// </summary>
        private static string ExtractRawObject(string json, string key)
        {
            string marker = "\"" + key + "\"";
            int keyIndex = json.IndexOf(marker, StringComparison.Ordinal);
            if (keyIndex < 0) return null;

            int colonIndex = json.IndexOf(':', keyIndex + marker.Length);
            if (colonIndex < 0) return null;

            int braceStart = json.IndexOf('{', colonIndex);
            if (braceStart < 0) return null;

            int depth = 0;
            for (int i = braceStart; i < json.Length; i++)
            {
                if (json[i] == '{')
                {
                    depth++;
                }
                else if (json[i] == '}')
                {
                    depth--;
                    if (depth == 0)
                    {
                        return json.Substring(braceStart, i - braceStart + 1);
                    }
                }
            }
            return null;
        }
    }
}
