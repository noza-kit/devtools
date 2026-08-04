using System;
using UnityEngine;
using UzBridge;

namespace UzBridge.Samples
{
    /// <summary>
    /// Example of consuming <see cref="UzBridgeClient.OnResultReceived"/>: if
    /// the Python server's pipeline includes the "color_range" step (see
    /// uzbridge.ops.color_range in the Python package), this moves
    /// <see cref="target"/> to track the detected blob's pixel position.
    ///
    /// Matches `uzbridge serve --step color_range`. Add more fields to
    /// ColorRangeResult / PipelineResults if you register more steps.
    /// </summary>
    [RequireComponent(typeof(UzBridgeClient))]
    public class ExampleResultConsumer : MonoBehaviour
    {
        [SerializeField] private Transform target;
        [SerializeField] private float pixelsToWorldScale = 0.01f;

        [Serializable]
        private class ColorRangeResult
        {
            public bool found;
            public int cx;
            public int cy;
        }

        [Serializable]
        private class PipelineResults
        {
            public ColorRangeResult color_range;
        }

        private UzBridgeClient _client;

        private void Awake()
        {
            _client = GetComponent<UzBridgeClient>();
        }

        private void OnEnable()
        {
            _client.OnResultReceived += HandleResult;
        }

        private void OnDisable()
        {
            _client.OnResultReceived -= HandleResult;
        }

        private void HandleResult(BridgeResult result)
        {
            if (!result.Success || string.IsNullOrEmpty(result.ResultsJson) || target == null)
            {
                return;
            }

            var results = JsonUtility.FromJson<PipelineResults>(result.ResultsJson);
            if (results?.color_range == null || !results.color_range.found)
            {
                return;
            }

            target.localPosition = new Vector3(
                results.color_range.cx * pixelsToWorldScale,
                -results.color_range.cy * pixelsToWorldScale,
                target.localPosition.z);
        }
    }
}
