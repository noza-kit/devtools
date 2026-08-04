"""Send one real test notification per channel, reading webhook URLs/tokens
from environment variables (SLACK_WEBHOOK_URL / DISCORD_WEBHOOK_URL /
LINE_CHANNEL_ACCESS_TOKEN + LINE_TO). Only prints success/failure per
channel - never the secret values themselves - so it's safe to run and
share the output.

Usage:
    SLACK_WEBHOOK_URL=... python scripts/smoketest.py slack
    python scripts/smoketest.py slack discord line
    python scripts/smoketest.py            # tries slack, discord, line
"""
from __future__ import annotations

import sys

from notify import notify


def main() -> int:
    channels = sys.argv[1:] or ["slack", "discord", "line"]
    results = notify("notify smoketest: 疎通確認", channels)

    ok = True
    for channel in channels:
        result = results[channel]
        if result.ok:
            print(f"{channel}: OK")
        else:
            ok = False
            print(f"{channel}: FAILED - {result.error}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
