# One hour revision

Tags: #python #revision #backend #hft

Use this as the final pass before the interview.

---

## Most important concepts

- Python names bind to objects; assignment does not copy.
- Mutability controls whether aliases observe changes.
- Mutable defaults are evaluated once and shared.
- Shallow copy creates a new outer container but shares nested objects.
- Deep copy recursively copies object graphs but can be expensive and unsafe for external resources.
- `is` checks identity; `==` checks value. Use `is None`.
- Tuples are only shallowly immutable.
- Dict/set keys must be hashable and hash-stable.
- Generator expressions and generators reduce memory for streaming data.
- Decorators are wrappers; use `functools.wraps`.
- Context managers guarantee cleanup.
- Catch specific exceptions and preserve stack traces.
- Retries need idempotency and deadlines.
- Threads help IO-bound work; multiprocessing helps CPU-bound Python.
- GIL limits parallel Python bytecode, not IO concurrency.
- Async improves high-concurrency IO; blocking calls stall the event loop.
- Stream large files and validate JSON carefully.
- `defaultdict`, `deque`, and `Counter` solve common interview/backend patterns.

---

## Most common Python backend interview mistakes

| Mistake | Better answer |
| --- | --- |
| Saying variables store values | Names reference objects |
| Saying tuples are always immutable | Tuple top-level is immutable; nested mutables can change |
| Using `is` for strings/ints | Use `==` except for singletons/sentinels |
| Ignoring mutable defaults | Use `None` and create fresh object |
| Blindly using `deepcopy` | Discuss cost, ownership, and alternatives |
| Catching `Exception` broadly | Catch specific errors and log context |
| Retrying every failure | Retry only transient/idempotent operations |
| Blocking in async handlers | Use async libraries or executors |
| Assuming GIL prevents races | Use locks/queues/ownership |
| Loading huge files/JSON into memory | Stream line-by-line or chunk |
| Overusing inheritance | Prefer composition for service dependencies |
| Overusing lambdas/comprehensions | Keep production code readable |

---

## Backend/HFT-specific Python tips

- Avoid hidden allocations in hot paths: repeated string concat, large `deepcopy`, building huge lists, excessive JSON roundtrips.
- Prefer explicit ownership of mutable state: one writer, clear boundaries, immutable snapshots.
- Always include request/order/correlation IDs in logs.
- Use monotonic clocks (`time.monotonic`) for timeouts and intervals.
- Separate "sent to exchange" from "acknowledged by exchange"; timeouts do not prove failure.
- Treat retries with care in trading systems: use idempotency keys/client order IDs.
- Use bounded queues/windows (`deque(maxlen=...)`) to avoid unbounded memory growth.
- Add timeouts to network calls; infinite waits become production incidents.
- Validate API payloads at boundaries; do not trust nested dicts.
- Benchmark before claiming performance improvements; Python intuition can be wrong.

---

## Mini code patterns to memorize

### Safe mutable default

```python
def append_item(item: str, items: list[str] | None = None) -> list[str]:
    if items is None:
        items = []
    items.append(item)
    return items
```

### Safe exception chaining

```python
class UpstreamError(Exception):
    pass

try:
    raise TimeoutError("exchange timed out")
except TimeoutError as exc:
    raise UpstreamError("quote lookup failed") from exc
```

### Async timeout and concurrency limit

```python
import asyncio

sem = asyncio.Semaphore(10)

async def call_with_limit(fn, *args):
    async with sem:
        return await asyncio.wait_for(fn(*args), timeout=0.5)
```

### Sliding window

```python
from collections import deque

window = deque(maxlen=100)
window.append(101.2)
```

### Top-k frequency

```python
from collections import Counter

top = Counter(["AAPL", "MSFT", "AAPL"]).most_common(1)
print(top)
```

---

## Last-minute explanation templates

Mutable vs immutable:

```text
Mutable objects can change in place, so aliases see changes. Immutable operations create new objects or rebind names. In backend services this matters because shared mutable request/config state can leak across requests.
```

Async:

```text
Async lets one event loop manage many IO waits by switching at await points. It improves throughput for IO-bound work but does not speed up CPU-heavy Python, and blocking calls can stall the loop.
```

GIL:

```text
The GIL allows one thread to execute Python bytecode at a time in CPython. Threads can still help IO-bound workloads, but CPU-bound Python usually needs multiprocessing, native code, or offloading.
```
