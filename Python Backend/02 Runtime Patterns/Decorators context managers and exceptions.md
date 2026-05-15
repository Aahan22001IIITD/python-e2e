# Decorators, context managers, and exceptions

Tags: #python #decorators #exceptions #context-managers #reliability #backend

These patterns are central to production Python services: logging, metrics, auth, retries, cleanup, resource ownership, and debugging.

---

## Decorators

### Concept

A decorator is a higher-order function that takes a function and returns a wrapped function.

Why backend systems care:

- Common in FastAPI/Flask route registration.
- Used for auth, logging, timing, metrics, retries, tracing, and circuit breakers.
- Wrappers must preserve metadata with `functools.wraps`.

### Basic runnable example

```python
from functools import wraps
from time import perf_counter

def timed(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed_ms = (perf_counter() - start) * 1000
            print(f"{fn.__name__} took {elapsed_ms:.2f}ms")
    return wrapper

@timed
def normalize(symbol: str) -> str:
    return symbol.strip().upper()

print(normalize(" aapl "))
```

Example output:

```text
normalize took 0.01ms
AAPL
```

The decorator runs code around the real function call without changing the call site. `finally` makes the timing log happen even if the wrapped function raises.

Without `@wraps`, logs, docs, traces, and frameworks may see the function name as `wrapper`.

### Auth/logging style decorator

```python
from functools import wraps

def require_role(role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(user: dict, *args, **kwargs):
            if role not in user.get("roles", []):
                raise PermissionError(f"missing role: {role}")
            return fn(user, *args, **kwargs)
        return wrapper
    return decorator

@require_role("trader")
def submit_order(user: dict, symbol: str) -> str:
    return f"accepted {symbol}"

print(submit_order({"roles": ["trader"]}, "AAPL"))
```

Output:

```text
accepted AAPL
```

The outer function receives the decorator argument (`"trader"`), the middle function receives the target function, and the wrapper checks the user before calling the target.

### FastAPI/Flask relevance

```python
# Flask style:
# @app.route("/health")
# def health():
#     return {"ok": True}

# FastAPI style:
# @app.get("/health")
# async def health():
#     return {"ok": True}
```

Framework decorators register functions with routing tables, dependency systems, and OpenAPI metadata.

### Things to keep in mind

- Always return the wrapped function's result and use `functools.wraps` so logs, docs, tracing, and frameworks see the original metadata.
- Async functions need async wrappers that `await fn(...)`; a normal wrapper changes the behavior in surprising ways.

Async decorator edge case:

```python
from functools import wraps
from time import perf_counter

def async_timed(fn):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        start = perf_counter()
        try:
            return await fn(*args, **kwargs)
        finally:
            print(f"{fn.__name__}: {(perf_counter() - start) * 1000:.2f}ms")
    return wrapper
```

### Quick revision

- Decorators wrap functions.
- Use `@wraps`.
- Common for logging, auth, metrics, retries, routing.
- Async functions need async wrappers.

---

## Context managers

### Concept

`with` guarantees setup and cleanup through `__enter__` and `__exit__`.

Why backend systems care:

- Files, DB sessions, locks, sockets, spans, and temporary resources must be released even on exceptions.
- Improves reliability and prevents leaks in long-running services.

### File example

```python
with open("example.txt", "w", encoding="utf-8") as f:
    f.write("hello\n")

# file is closed even if an exception occurs inside the block
```

### Custom context manager class

```python
class Connection:
    def __enter__(self):
        print("open")
        return self

    def __exit__(self, exc_type, exc, tb):
        print("close")
        return False  # do not suppress exceptions

    def send(self, msg: str) -> None:
        print(f"send {msg}")

with Connection() as conn:
    conn.send("order")
```

Output:

```text
open
send order
close
```

`__enter__` acquires the resource and returns the object used inside the block. `__exit__` runs after the block, even when the block fails, which is why this pattern is common for files, locks, DB sessions, and tracing spans.

### `contextlib` version

```python
from contextlib import contextmanager

@contextmanager
def lock_name(name: str):
    print(f"acquire {name}")
    try:
        yield
    finally:
        print(f"release {name}")

with lock_name("risk"):
    print("critical section")
```

Output:

```text
acquire risk
critical section
release risk
```

The code before `yield` is setup, and the `finally` block is cleanup. This is often simpler than writing a full class when the context manager only wraps one resource.

### Edge case: suppressing exceptions

```python
class SuppressValueError:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return exc_type is ValueError

with SuppressValueError():
    raise ValueError("hidden")

print("continued")
```

Output:

```text
continued
```

Warning: returning `True` from `__exit__` suppresses the exception. Use this narrowly and log intentionally, because hidden exceptions can hide incidents.

### Quick revision

- Use `with` for resource ownership.
- `__exit__` always runs.
- Returning `True` from `__exit__` suppresses exceptions.
- Context managers reduce leaks and cleanup bugs.

---

## Exception handling

### Concept

Handle exceptions where you can add context, recover, retry, or translate to a domain/API error.

Why backend systems care:

- Production debugging depends on preserving stack traces and logging useful context.
- Retry logic must distinguish transient failures from permanent failures.
- Bad exception handling causes silent data loss and impossible incidents.

### Good pattern

```python
import logging

logger = logging.getLogger(__name__)

class ExchangeUnavailable(Exception):
    pass

def call_exchange(symbol: str) -> dict:
    raise TimeoutError("socket timeout")

def get_quote(symbol: str) -> dict:
    try:
        return call_exchange(symbol)
    except TimeoutError as exc:
        logger.warning("exchange timeout", extra={"symbol": symbol})
        raise ExchangeUnavailable(symbol) from exc
```

`raise ... from exc` preserves the causal chain: callers see the domain error, and debugging still has the original timeout.

### Bad pattern

```python
try:
    result = call_exchange("AAPL")
except Exception:
    result = None  # bug: hides failure, loses stack/context
```

### Retry pattern

```python
import time
from collections.abc import Callable

def retry(fn: Callable[[], str], attempts: int = 3) -> str:
    last_error: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except TimeoutError as exc:
            last_error = exc
            time.sleep(0.05 * (2 ** i))
    raise RuntimeError("operation failed after retries") from last_error
```

Production note: add jitter, deadlines, idempotency checks, and metrics. Do not blindly retry non-idempotent order submissions.

### `try` / `except` / `finally`

```python
resource = "socket"
try:
    print("use", resource)
except OSError as exc:
    print("network failure", exc)
finally:
    print("cleanup always runs")
```

Output:

```text
use socket
cleanup always runs
```

### Things to keep in mind

- Catch specific exceptions where you can add context, recover, retry, or translate the error for a caller.
- Preserve stack traces with `raise` or `raise ... from exc`; avoid `except Exception: pass` because it turns real failures into silent bad state.

### Quick revision

- Catch specific exceptions.
- Add context, then re-raise or translate.
- Preserve stack traces with `raise` or `raise ... from exc`.
- Always distinguish transient vs permanent errors.
- Retry only when operation semantics are safe.
