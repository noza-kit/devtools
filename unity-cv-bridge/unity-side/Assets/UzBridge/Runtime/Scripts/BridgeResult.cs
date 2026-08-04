using System;

namespace UzBridge
{
    /// <summary>
    /// A processed result from the Python pipeline, flattened for easy
    /// consumption. <see cref="ResultsJson"/> is the raw JSON text of the
    /// "results" object -- its shape depends on which pipeline steps are
    /// registered on the Python side, so parse it with your own
    /// [Serializable] class via JsonUtility.FromJson, e.g.:
    /// <code>
    /// [Serializable] class ColorRangeStep { public bool found; public int cx; public int cy; }
    /// [Serializable] class MyResults { public ColorRangeStep color_range; }
    /// var parsed = JsonUtility.FromJson&lt;MyResults&gt;(result.ResultsJson);
    /// </code>
    /// </summary>
    [Serializable]
    public struct BridgeResult
    {
        public bool Success;
        public string Status;
        public int FrameId;
        public double Timestamp;
        public string ResultsJson;
    }
}
