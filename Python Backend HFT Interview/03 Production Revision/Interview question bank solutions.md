# Interview question bank solutions

Tags: #python #interview #solutions #backend #hft

Use these as spoken-answer templates. Keep answers concise in the interview, then expand with one code example if asked.

---

## 1. Mutable vs immutable objects

Mutable objects can change in place; immutable objects cannot. Python names hold references to objects, so if two names reference the same mutable object, mutation through one name is visible through the other.

Why it matters: backend services often pass nested request/config dictionaries between functions. Accidental mutation can leak state between middleware, retries, background tasks, or tests.

```python
def add_check(config: dict) -> None:
    config["checks"].append("max_qty")

base = {"checks": []}
alias = base
add_check(alias)

print(base)  # {'checks': ['max_qty']}
```

Safe pattern: copy at boundaries or use immutable snapshots.

---

## 2. Mutable default arguments

Default arguments are evaluated once at function definition time, so a mutable default is shared across calls.

```python
def bad(symbol: str, seen: list[str] = []):
    seen.append(symbol)
    return seen

print(bad("AAPL"))  # ['AAPL']
print(bad("MSFT"))  # ['AAPL', 'MSFT']
```

Fix:

```python
def good(symbol: str, seen: list[str] | None = None) -> list[str]:
    if seen is None:
        seen = []
    seen.append(symbol)
    return seen
```

Production bug: cross-request state leakage in long-running workers.

---

## 3. Shallow copy vs deep copy

Assignment shares the same object. Shallow copy creates a new outer container but shares nested objects. Deep copy recursively copies the reachable object graph.

```python
import copy

base = {"risk": {"checks": []}}
shallow = base.copy()
shallow["risk"]["checks"].append("max_qty")
print(base)  # nested list changed

deep = copy.deepcopy(base)
deep["risk"]["checks"].append("price_band")
print(base)  # unchanged by deep copy
```

Interview trap: `.copy()` on a dict is not enough for nested dict/list structures.

---

## 4. When to avoid `copy.deepcopy`

Avoid `deepcopy` in hot paths, large object graphs, low-latency loops, and objects with external resources like locks, sockets, DB sessions, file handles, or thread pools.

Better alternatives:

- Build fresh small objects explicitly.
- Use immutable templates.
- Copy only the fields that need isolation.
- Use ownership rules: one component owns mutation.

```python
def build_order_fast(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "risk": {"checks": ["max_qty", "price_band"]},
    }
```

HFT point: blind deep copies can create allocation spikes and tail-latency outliers.

---

## 5. `is` vs `==`

`is` checks identity: same object. `==` checks value equality through `__eq__`.

```python
a = [1, 2]
b = [1, 2]

print(a == b)  # True
print(a is b)  # False
```

Use `is None` because `None` is a singleton and `== None` can call custom equality logic.

```python
if timeout is None:
    timeout = 1.0
```

---

## 6. Interning and identity traps

CPython may intern/cache small integers and some strings, so `a is b` can appear true for equal values. This is an implementation optimization, not a correctness rule.

```python
x = 256
y = 256

print(x == y)  # True
# x is y may be True in CPython; do not rely on it.
```

Production rule: use `==` for values, `is` for singletons/sentinels.

---

## 7. `list` vs `tuple`

Lists are mutable and good for growing/changing collections. Tuples are immutable at the top level and good for fixed records, snapshots, and hashable composite keys if all elements are hashable.

```python
route = {
    ("NASDAQ", "AAPL"): "nasdaq-connector",
}

orders = []
orders.append(("AAPL", 100))
```

Performance: tuples are often smaller; lists over-allocate for append growth. Choose based on data model first.

---

## 8. Tuple containing mutable objects

A tuple prevents replacing elements, but it does not freeze mutable objects inside it.

```python
t = (["AAPL"], "strategy-a")
t[0].append("MSFT")

print(t)  # (['AAPL', 'MSFT'], 'strategy-a')
```

Bug: treating such tuples as safe immutable records can lead to hidden shared-state mutation.

---

## 9. `set` vs `dict`

Both are hash-table based. Sets store unique values. Dicts store key-value mappings.

```python
seen_ids: set[str] = set()
routes: dict[tuple[str, str], str] = {
    ("NASDAQ", "AAPL"): "connector-1",
}
```

Average lookup/insert/delete is O(1), assuming good hashing. Values used in sets/dict keys must be hashable and stable.

Backend uses:

- Set: dedupe IDs, allowed symbols, feature flags.
- Dict: caches, routing tables, request/order state.

---

## 10. Mutating dict keys

Dicts locate keys by hash and equality. If an object’s hash/equality changes after insertion, lookup can break.

```python
class Key:
    def __init__(self, symbol: str):
        self.symbol = symbol

    def __hash__(self):
        return hash(self.symbol)

    def __eq__(self, other):
        return isinstance(other, Key) and self.symbol == other.symbol

k = Key("AAPL")
d = {k: "route"}
k.symbol = "MSFT"

print(d.get(k))  # often None
```

Safe pattern: use immutable keys like strings, ints, or tuples of immutable values.

---

## 11. Comprehensions and generator expressions

Comprehensions build collections concisely. Generator expressions are lazy and avoid materializing intermediate lists.

```python
orders = [{"symbol": "AAPL", "qty": 10}, {"symbol": "MSFT", "qty": 0}]

symbols = [o["symbol"] for o in orders]
active = {o["symbol"] for o in orders if o["qty"] > 0}
qty_by_symbol = {o["symbol"]: o["qty"] for o in orders}
total = sum(o["qty"] for o in orders)  # generator expression
```

Use generators for large files/logs or streaming pipelines.

---

## 12. Comprehensions vs `map`/`filter`/`lambda`

In Python, comprehensions are usually more readable for simple transformations and filters. `map`/`filter` are lazy in Python 3 and can be useful with named functions.

```python
symbols = [o["symbol"] for o in orders if o["qty"] > 0]

def normalize(symbol: str) -> str:
    return symbol.strip().upper()

clean = list(map(normalize, [" aapl ", " msft "]))
```

Avoid complex lambdas in production code because they hurt readability and stack traces.

---

## 13. Iterators and `StopIteration`

An iterable can produce an iterator via `iter()`. An iterator returns values with `next()` and raises `StopIteration` when exhausted.

```python
it = iter([1, 2])
print(next(it))  # 1
print(next(it))  # 2
# next(it)       # StopIteration
```

Production relevance: file handles, DB cursors, paginated APIs, and streaming responses are iterator-like. Remember iterators are one-pass.

---

## 14. Generators and `yield`

A generator is a lazy iterator defined with `yield`. It keeps function state between values.

```python
def valid_lines(lines: list[str]):
    for line in lines:
        line = line.strip()
        if line:
            yield line

print(list(valid_lines(["AAPL", "", "MSFT"])))
```

Why it matters: generators stream large data without loading all rows/events/logs into memory.

---

## 15. Timing/logging decorator

A decorator wraps a function. `functools.wraps` preserves metadata such as name, docstring, and annotations.

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
            print(f"{fn.__name__} took {(perf_counter() - start) * 1000:.2f}ms")
    return wrapper
```

Backend relevance: auth, metrics, tracing, request logging, retries, and FastAPI/Flask routing.

---

## 16. Context managers

Context managers handle setup/cleanup around a block using `__enter__` and `__exit__`.

```python
class Resource:
    def __enter__(self):
        print("open")
        return self

    def __exit__(self, exc_type, exc, tb):
        print("close")
        return False

with Resource():
    print("use")
```

`__exit__` runs even on exceptions. Returning `True` suppresses the exception; usually avoid this unless intentional.

---

## 17. Production exception handling

Catch specific exceptions, log useful context, preserve stack traces, and translate to domain errors when needed.

```python
import logging

logger = logging.getLogger(__name__)

class ExchangeUnavailable(Exception):
    pass

def get_quote(symbol: str):
    try:
        raise TimeoutError("timeout")
    except TimeoutError as exc:
        logger.warning("quote timeout", extra={"symbol": symbol})
        raise ExchangeUnavailable(symbol) from exc
```

Avoid `except Exception: pass`; it hides failures and destroys debugging context.

---

## 18. Safe retry pattern and order-submission risk

Retries should handle transient errors with backoff, deadlines, logging, and idempotency. They are dangerous for order submission because a timeout does not prove the exchange rejected the order.

```python
import time

def retry_timeout(fn, attempts: int = 3):
    last_error = None
    for i in range(attempts):
        try:
            return fn()
        except TimeoutError as exc:
            last_error = exc
            time.sleep(0.05 * (2 ** i))
    raise RuntimeError("operation timed out") from last_error
```

Trading answer: use client order IDs/idempotency keys, reconcile order state, and do not blindly resubmit.

---

## 19. `*args` and `**kwargs`

`*args` captures positional extras. `**kwargs` captures keyword extras. They are useful for decorators and adapters but can make public APIs unclear.

```python
def log_event(event: str, *tags: str, **fields) -> None:
    print(event, tags, fields)

log_event("order.accepted", "trading", venue="NASDAQ", symbol="AAPL")
```

Public backend APIs should prefer explicit typed parameters when possible.

---

## 20. `classmethod` vs `staticmethod`

`classmethod` receives `cls` and is good for alternative constructors/factories. `staticmethod` receives no implicit argument and is a namespaced helper.

```python
class Client:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    @classmethod
    def from_config(cls, config: dict):
        return cls(config["endpoint"])

    @staticmethod
    def normalize_venue(venue: str) -> str:
        return venue.strip().upper()
```

Use `classmethod` when subclassing should preserve the concrete class.

---

## 21. Inheritance vs composition

Inheritance models an `is-a` relationship. Composition builds behavior by holding dependencies.

```python
class Connector:
    def send_order(self, symbol: str, qty: int) -> str:
        raise NotImplementedError

class MockConnector(Connector):
    def send_order(self, symbol: str, qty: int) -> str:
        return "accepted"

class OrderService:
    def __init__(self, connector: Connector):
        self.connector = connector
```

Backend answer: use polymorphism for connector interfaces, but prefer composition for services so dependencies can be tested/replaced.

---

## 22. Threading vs multiprocessing

Threads share memory and are good for IO-bound work. Processes have separate memory and are better for CPU-bound Python work because they avoid the GIL limitation.

```python
import threading

def io_task(symbol: str):
    print("fetch", symbol)

threads = [threading.Thread(target=io_task, args=(s,)) for s in ["AAPL", "MSFT"]]
for t in threads: t.start()
for t in threads: t.join()
```

Tradeoff: multiprocessing adds serialization, startup cost, and memory overhead.

---

## 23. GIL

The Global Interpreter Lock allows only one thread to execute Python bytecode at a time in CPython.

Correct answer:

- It limits CPU-bound parallelism in pure Python threads.
- It does not prevent logical race conditions.
- IO-bound threads can still help because blocking IO releases control.
- CPU-heavy work usually needs multiprocessing, native extensions, or another service.

```python
# balance += amount is read-modify-write logic; protect shared state with a lock.
```

---

## 24. `async` / `await` and FastAPI

`async def` defines a coroutine. `await` yields control to the event loop while waiting for IO. This lets one process handle many concurrent network waits.

```python
import asyncio

async def fetch(symbol: str) -> str:
    await asyncio.sleep(0.05)
    return f"{symbol}=100"

async def main():
    print(await asyncio.gather(fetch("AAPL"), fetch("MSFT")))

asyncio.run(main())
```

FastAPI benefits when handlers call async DB/HTTP clients. Blocking calls like `time.sleep()` or sync DB drivers can stall the event loop.

---

## 25. JSON and large file handling

Parse JSON with explicit error handling and validate schema after parsing. Stream large files instead of reading everything into memory.

```python
import json

def parse_order(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON") from exc

    if "symbol" not in data or "qty" not in data:
        raise ValueError("missing required fields")
    return data
```

Large file pattern:

```python
def read_lines(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            yield line.rstrip("\n")
```

Financial systems note: avoid floats for money when exactness matters; use `Decimal` or integer ticks/cents depending on system design.

---

## Coding prompt 1. Mutable default bug

The bug is that `seen=[]` is created once when the function is defined, not once per call. Every call that does not pass `seen` mutates the same list.

```python
def add_seen(symbol: str, seen: list[str] | None = None) -> list[str]:
    if seen is None:
        seen = []
    seen.append(symbol)
    return seen
```

Interview answer: this can leak state between requests in a long-running backend worker. Use `None` as the sentinel and create a fresh list inside the function.

---

## Coding prompt 2. Shallow copy bug

`dict.copy()` creates a new outer dictionary, but nested objects are still shared. Here `base["risk"]` and `order["risk"]` point to the same nested dict, so appending to `checks` changes both.

```python
base = {"risk": {"checks": []}}

order = {
    "risk": {
        "checks": list(base["risk"]["checks"]),
    }
}
order["risk"]["checks"].append("max_qty")

print(base)   # {'risk': {'checks': []}}
print(order)  # {'risk': {'checks': ['max_qty']}}
```

Production answer: prefer explicit construction for small objects. Use `copy.deepcopy` only when the object graph is truly dynamic and the allocation cost is acceptable.

---

## Coding prompt 3. Dict key mutation

The key's hash is based on `symbol`. After insertion, changing `symbol` changes the hash/equality behavior, so the dict may no longer find the object in the bucket where it was stored.

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Key:
    symbol: str

k = Key("AAPL")
d = {k: "route"}

print(d.get(Key("AAPL")))  # route
```

Safe pattern: use immutable keys such as strings, integers, tuples of immutable values, or frozen dataclasses.

---

## Coding prompt 4. Async blocking bug

`time.sleep(1)` blocks the whole event loop. While it sleeps, other async requests cannot make progress in that worker.

```python
import asyncio

async def handler():
    await asyncio.sleep(1)
    return {"ok": True}
```

If the real work is blocking IO or CPU-bound code, do not just wrap it in `async def`. Use an async library for IO, or move blocking work out of the event loop:

```python
import asyncio

def blocking_call() -> dict:
    return {"ok": True}

async def handler():
    return await asyncio.to_thread(blocking_call)
```

Backend answer: async improves IO concurrency only when waits yield to the event loop.

---

## Coding prompt 5. Retry semantics

This retry loop is dangerous because `TimeoutError` means the client did not receive a response. It does not mean the exchange failed to receive or process the order. Blindly retrying can duplicate an order.

```python
import time
from collections.abc import Callable

def submit_order_with_reconcile(
    order: dict,
    send: Callable[[dict], str],
    lookup_by_client_id: Callable[[str], str | None],
    attempts: int = 3,
) -> str:
    client_order_id = order["client_order_id"]
    last_error: TimeoutError | None = None

    for attempt in range(attempts):
        try:
            return send(order)
        except TimeoutError as exc:
            last_error = exc
            known_status = lookup_by_client_id(client_order_id)
            if known_status is not None:
                return known_status
            time.sleep(0.05 * (2 ** attempt))

    raise RuntimeError("order status unknown after retries") from last_error
```

Trading answer: assign a stable client order ID before sending, retry only if the operation is idempotent, reconcile with the exchange/order store after timeouts, and surface an "unknown" state instead of pretending the order failed.
