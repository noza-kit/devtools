using NetMQ;
using UnityEngine;

namespace UzBridge
{
    /// <summary>
    /// NetMQ under Unity needs <c>AsyncIO.ForceDotNet.Force()</c> called before
    /// any socket is created (forces the pure .NET transport instead of a
    /// native one Unity doesn't ship), and <c>NetMQConfig.Cleanup()</c> called
    /// once before the process exits, or the editor/player can hang on
    /// stop/quit. This is shared, process-wide setup, so it's guarded to run
    /// once no matter how many <see cref="UzBridgeClient"/> instances exist.
    /// </summary>
    internal static class NetMqCleanup
    {
        private static bool _initialized;

        public static void EnsureInitialized()
        {
            if (_initialized) return;
            _initialized = true;

            AsyncIO.ForceDotNet.Force();
            Application.quitting += () => NetMQConfig.Cleanup(false);
        }
    }
}
