# LogFix Python SDK

[![PyPI version](https://badge.fury.io/py/logfix.svg)](https://pypi.org/project/logfix/)
[![Python Support](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)

Python errors, explained. The official SDK for LogFix — turn cryptic stack traces into actionable solutions in 30 seconds.

---

## Installation

Install the SDK via pip:

```bash
pip install logfix
```

---

## Quickstart

Call `logfix.init()` before your app starts handling requests.

```python
import logfix

logfix.init(
    api_key="logfix_api_key",
    app_version="1.2.3",
)

try:
    result = 1 / 0
except Exception as e:
    logfix.capture_error(e, tags={"region": "ap-northeast-2"})

# Make sure all queued events are sent before exiting
logfix.flush()
```

---

## Configuration Options

You can customize the SDK's behavior by passing the following options to `logfix.init()`:

| Option | Type | Default | Description |
|---|---|---|---|
| `api_key` | `str` | **(Required)** | Your project's API Key. |
| `app_version` | `str` | `"unknown"` | Your application's version tag. |
| `endpoint` | `str` | `https://api.logfix.xyz` | URL for self-hosted servers. |
| `max_batch_size` | `int` | `50` | Maximum number of events sent in a single batch. |
| `flush_interval` | `float` | `5.0` | Periodic flush interval (in seconds). |
| `queue_size` | `int` | `1000` | Internal event buffer size. |
| `max_retries` | `int` | `3` | Maximum retry attempts for failed transmissions. |
| `overflow_policy` | `str` | `"drop_newest"` | Behavior when the queue is full: `drop_newest`, `drop_oldest`, or `block`. |
| `debug` | `bool` | `False` | Enable SDK internal debug logging. |
| `enabled` | `bool` | `True` | Set to `False` to disable capturing (useful for testing/local dev). |

---

## Usage

### Capturing Errors & Messages

```python
# Basic error capture
logfix.capture_error(exc)

# Capture with custom level, tags, and extra context
logfix.capture_error(
    exc,
    level=logfix.Level.WARNING,
    tags={"user_id": "usr_123"},
    extra={"plan": "enterprise"},
)

# Capture a text message directly
logfix.capture_message("Deployment started", level=logfix.Level.INFO)

# Automatically recover and capture panics (useful for callbacks/threads)
logfix.recover_and_capture(lambda: risky_function())

# Context manager for automatic exception capturing
with logfix.capture_exceptions(reraise=False):
    risky_operation()
```

---

## Framework Integrations

LogFix provides built-in middleware for popular Python web frameworks to automatically capture unhandled exceptions.

### Flask

```python
from flask import Flask
from logfix.middleware.flask import LogfixFlaskMiddleware

app = Flask(__name__)
LogfixFlaskMiddleware(app)
```

### FastAPI

```python
from fastapi import FastAPI
from logfix.middleware.fastapi import LogfixFastAPIMiddleware

app = FastAPI()
app.add_middleware(LogfixFastAPIMiddleware)
```

### Django

Add the middleware to your `settings.py`:
```python
MIDDLEWARE = [
    # ... other middleware ...
    'logfix.middleware.django.LogfixDjangoMiddleware',
]
```

---

## Testing Environment

When running unit tests or working locally, you can disable the SDK so it doesn't send events to the LogFix servers.

```python
logfix.init(api_key="lf_test", enabled=False)

# When enabled=False, all capture functions become safe no-ops.
```

---

## API Compatibility

| SDK Version | LogFix Core API | Server API |
|---|---|---|
| 1.x | v1 | v1.3 |

---

## License

[MIT](LICENSE)
