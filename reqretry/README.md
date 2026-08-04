# reqretry

A thin wrapper around [`requests`](https://requests.readthedocs.io/) that adds
configurable exponential-backoff retries (timeouts, 5xx responses, connection
errors) and a default request timeout, so a flaky endpoint doesn't need
hand-rolled retry loops at every call site — and a forgotten timeout doesn't
hang forever.

## Install

```bash
cd reqretry
pip install -e ".[dev]"
```

From GitHub (this package lives in the `reqretry/` subdirectory of the repo):

```bash
pip install "git+https://github.com/noza-kit/devtools.git#subdirectory=reqretry"
```

## Usage

Same calling convention as `requests` itself:

```python
import reqretry

resp = reqretry.get("https://api.example.com/data")
resp = reqretry.post("https://api.example.com/data", json={"key": "value"})
```

Calls that fail with a timeout, a connection error, or a 5xx response are
retried with exponential backoff — by default up to 3 retries, waiting 1s,
then 2s, then 4s. Non-5xx responses (4xx, etc.) are returned as-is on the
first try, same as `requests` — call `resp.raise_for_status()` yourself if
you want those to raise.

Every call also gets a default 10s timeout if you don't pass one, so a hung
connection can't block forever.

### Configuring retries globally

```python
reqretry.configure(max_retries=5, backoff_factor=0.5, timeout=30)
```

### Configuring retries per Session

Use a `Session` to reuse a connection pool (recommended for many calls to the
same host) and/or to scope retry settings to just that session:

```python
from reqretry import RetryConfig, Session

session = Session(RetryConfig(
    max_retries=5,
    backoff_factor=0.5,       # first wait, in seconds
    backoff_multiplier=2.0,   # doubles each retry: 0.5s, 1s, 2s, 4s, 8s
    retry_status_codes={429, 500, 502, 503, 504},
    timeout=15,
))
resp = session.get("https://api.example.com/data")
```

### Configuring retries per call

```python
resp = reqretry.get(url, retry_config=RetryConfig(max_retries=0))  # no retries for this call
```

## `RetryConfig` fields

| Field | Default | Meaning |
| --- | --- | --- |
| `max_retries` | `3` | Retries after the first attempt (4 attempts total by default) |
| `backoff_factor` | `1.0` | Wait (seconds) before the first retry |
| `backoff_multiplier` | `2.0` | Multiplies the wait after each retry (`1.0` -> `2.0` -> `4.0`...) |
| `retry_status_codes` | all of `500`-`599` | Response status codes that trigger a retry |
| `retry_exceptions` | `Timeout`, `ConnectionError` | Exception types that trigger a retry |
| `timeout` | `10.0` | Applied when a call doesn't pass its own `timeout` |

## Logging

Each retry logs a `WARNING` to the `"reqretry"` logger with the attempt
count and wait time, e.g.:

```
GET https://api.example.com/data returned 503; retry 1/3 in 1.0s
```

Enable it with the standard `logging` module:

```python
import logging
logging.getLogger("reqretry").setLevel(logging.WARNING)
logging.basicConfig()
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests use the [`responses`](https://github.com/getsentry/responses) library
to mock HTTP responses/exceptions and monkeypatch `time.sleep` so retry
behavior is verified without real network calls or real waiting.
