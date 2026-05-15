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

### Interview traps/questions

- What is a closure?
  Answer: A closure is a function that remembers variables from its enclosing scope after that scope has returned. Decorators use this to keep access to the wrapped function or decorator arguments.
- Why use `functools.wraps`?
  Answer: `functools.wraps` copies metadata like `__name__`, `__doc__`, annotations, and `__wrapped__`, which helps logs, docs, debuggers, tracing, and web frameworks.
- How do decorators with arguments work?
  Answer: A decorator with arguments is usually three layers: the outer function receives decorator config, the middle function receives the target function, and the inner wrapper runs around the target call.
- How do you preserve return values and exceptions?
  Answer: Preserve return values with `return fn(...)`; preserve exceptions by not swallowing them unless intentional. Use `try` / `finally` for cleanup or timing that must happen on both success and failure.
- Can decorators wrap async functions?
  Answer: Yes, but the wrapper must be `async def` and must `await fn(...)`; otherwise the decorator returns a coroutine object without executing it correctly.

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

Production warning: suppressing exceptions can hide incidents. Use narrowly and log intentionally.

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

`raise ... from exc` preserves causal chains.

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

### Interview traps/questions

- Why is `except Exception: pass` dangerous?
  Answer: `except Exception: pass` hides bugs, loses stack traces, and can make failed orders, dropped messages, or bad state look successful.
- When should you use custom exceptions?
  Answer: Use custom exceptions at domain boundaries when callers need to distinguish business failures from low-level errors, such as `ExchangeUnavailable`, `RiskLimitExceeded`, or `InvalidOrder`.
- What is exception chaining?
  Answer: Exception chaining links a higher-level error to the original cause with `raise NewError(...) from exc`, preserving debugging context across abstraction layers.
- Which operations are safe to retry?
  Answer: Retrying is safe for transient failures only when the operation is idempotent or has deduplication/idempotency keys. Blindly retrying order placement can duplicate trades.
- Why should logs include correlation/order/request IDs?
  Answer: Correlation, order, and request IDs let you connect logs across services, retries, queues, and exchange calls during incident debugging.

### Quick revision

- Catch specific exceptions.
- Add context, then re-raise or translate.
- Preserve stack traces with `raise` or `raise ... from exc`.
- Always distinguish transient vs permanent errors.
- Retry only when operation semantics are safe.
