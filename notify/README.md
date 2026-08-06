# notify

Send a message to Slack, Discord, LINE (via a LINE Official Account /
Messaging API), and/or the desktop from one call, with retrying/timeout-protected
HTTP delivery via
[`reqretry`](../reqretry). Built for "job finished" pings from long-running
scripts (training runs, batch jobs, etc.) that shouldn't crash just because a
webhook is briefly down.

## Install

```bash
cd notify
pip install -e ../reqretry   # local dependency, not on PyPI
pip install -e ".[dev]"
```

## Usage

```python
from notify import notify

notify("学習が完了しました")                          # desktop only (default)
notify("バッチ処理完了", channels=["discord", "line"])  # fan out to multiple channels
```

`notify()` never raises. It returns a `dict[str, ChannelResult]` so you can
check what happened:

```python
results = notify("hello", channels=["slack", "line"])
for channel, result in results.items():
    if not result.ok:
        print(f"{channel} failed: {result.error}")
```

### Channels and their configuration

Each channel reads its webhook URL/token from an environment variable, or
from a `config` object passed to `notify()` (any dict or dict-like object,
e.g. a [`confload`](../confload) `Config` — looked up by lowercased key):

| Channel | Env var | Config key |
| --- | --- | --- |
| `slack` | `SLACK_WEBHOOK_URL` | `slack_webhook_url` |
| `discord` | `DISCORD_WEBHOOK_URL` | `discord_webhook_url` |
| `line` | `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_TO` | `line_channel_access_token`, `line_to` |
| `desktop` | *(none — uses [`plyer`](https://github.com/kivy/plyer) locally)* | |

`line` pushes via the [Messaging API](https://developers.line.biz/en/reference/messaging-api/#send-push-message)
(`POST https://api.line.me/v2/bot/message/push`), using a channel access
token issued for a LINE Official Account in the
[LINE Developers console](https://developers.line.biz/console/), plus the
target `userId`/`groupId`/`roomId` to push to (`LINE_TO`). LINE Notify, the
older token-only API, was discontinued in 2025.

### Getting webhook URLs / tokens

#### Slack

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New
   App** → **From scratch**. Name it and pick the workspace to install it
   into.
2. In the app's left sidebar, open **Incoming Webhooks** and toggle
   **Activate Incoming Webhooks** on.
3. Click **Add New Webhook to Workspace**, pick the channel it should post
   to, and click **Allow**.
4. Copy the generated URL (`https://hooks.slack.com/services/...`) and set
   it as `SLACK_WEBHOOK_URL`. Each webhook is tied to one channel — repeat
   from step 3 (same app) to get a webhook for another channel.

#### Discord

1. In the target Discord server, open **Server Settings → Integrations →
   Webhooks → New Webhook**.
2. Name it and pick the channel it should post to.
3. Click **Copy Webhook URL** and set it as `DISCORD_WEBHOOK_URL`.

#### LINE

1. Sign in to the [LINE Developers console](https://developers.line.biz/console/),
   create a Provider (if you don't have one yet), then create a new
   **Messaging API** channel under it, filling in the required name/category/icon.
2. Open the channel → **Messaging API** tab → **Channel access token**
   section → **Issue** a long-lived token. Copy it as
   `LINE_CHANNEL_ACCESS_TOKEN`.
3. On the same tab, scan the channel's QR code with your phone's LINE app
   to add the Official Account as a friend — a push message fails if the
   recipient hasn't friended it first. (Optional: disable "Auto-reply
   messages" / "Greeting messages" in the **LINE Official Account
   Manager** so the OA doesn't respond to your own test messages.)
4. Find the target `userId` (or `groupId`/`roomId`) for `LINE_TO`. The
   console doesn't display this directly — the standard way is to
   temporarily point the channel's **Webhook URL** (Messaging API tab) at
   an endpoint you control (e.g. a quick `ngrok`-tunneled local server),
   send the OA a message from the account/group you want to notify, and
   read `events[0].source.userId` (or `.groupId`/`.roomId`) from the
   incoming webhook payload.

```python
from confload import load_config
from notify import notify

config = load_config("secrets.yaml")  # slack_webhook_url: ..., line_channel_access_token: ..., line_to: ...
notify("done", channels=["slack", "line"], config=config)
```

A missing webhook URL/token raises internally but is caught and reported as
a failed `ChannelResult` — it will not stop other channels from being tried
or crash the calling program.

### Retry behavior

HTTP channels (`slack`, `discord`, `line`) send through `reqretry`'s default
session, so a timeout, connection error, or 5xx response is retried with
exponential backoff before being treated as a failure. See
[reqretry's README](../reqretry/README.md) for the retry/backoff defaults and
how to change them (`reqretry.configure(...)`).

## `notify_on_complete` decorator

```python
from notify import notify_on_complete

@notify_on_complete("学習が完了しました", channels=["discord"])
def train():
    ...  # long-running training loop
```

Sends a notification when the function returns, including its name and
elapsed time. By default it also notifies (with the exception message) if the
function raises, then re-raises the original exception unchanged — pass
`notify_on_error=False` to only notify on success.

## Development

```bash
pip install -e ../reqretry
pip install -e ".[dev]"
pytest
```

Tests use [`responses`](https://github.com/getsentry/responses) to mock the
Slack/Discord/LINE HTTP calls and monkeypatch `plyer.notification.notify` for
the desktop channel, so no real network calls or system notifications happen.
