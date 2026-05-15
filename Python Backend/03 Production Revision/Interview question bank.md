# Interview question bank

Tags: #python #interview #backend #hft #revision

Use these to rehearse out loud. Strong answers should include: definition, production relevance, example bug, performance/concurrency angle, and safe pattern.

Solutions: [[Interview question bank solutions]]

---

## Top 25 likely questions

### 1. Explain mutable vs immutable objects in Python. Give a backend bug caused by accidental mutation.

Answer: mutable objects can change in place; immutable objects cannot. Python names reference objects, so aliases to the same list/dict will all observe mutation. A backend bug is mutating a shared request/config dict in middleware and leaking that state into retries, background jobs, or later requests.

### 2. Why are mutable default arguments dangerous? Write the bug and the fix.

Answer: defaults are evaluated once when the function is defined, so a default list/dict is shared across calls.

```python
def bad(symbol: str, seen: list[str] = []):
    seen.append(symbol)
    return seen

def good(symbol: str, seen: list[str] | None = None) -> list[str]:
    if seen is None:
        seen = []
    seen.append(symbol)
    return seen
```

### 3. What is the difference between shallow copy and deep copy? What happens with nested dictionaries?

Answer: a shallow copy creates a new outer container but shares nested objects. A deep copy recursively copies nested objects. With nested dictionaries, `base.copy()` does not isolate inner dicts/lists, so mutating `copy["risk"]["checks"]` can mutate `base["risk"]["checks"]`.

### 4. When would you avoid `copy.deepcopy` in a low-latency service?

Answer: avoid it in hot paths, large object graphs, and objects containing locks, sockets, sessions, or file handles. It can create allocation spikes and tail latency. Prefer explicit fresh construction, immutable templates, or copying only the fields that need isolation.

### 5. Explain `is` vs `==`. Why should checks against `None` use `is None`?

Answer: `is` checks object identity; `==` checks value equality through `__eq__`. Use `is None` because `None` is a singleton and `== None` can call custom equality logic.

### 6. Why might `a is b` appear true for small integers or strings? Should production code rely on that?

Answer: CPython may cache small integers and intern some strings, so two equal values can sometimes be the same object. This is an implementation optimization, not a correctness rule. Use `==` for values and `is` only for singletons/sentinels.

### 7. Compare `list` and `tuple`: mutability, memory, hashing, and production use cases.

Answer: lists are mutable and useful for growing/changing collections. Tuples are immutable at the top level, often smaller, and can be hashable if every element is hashable. Use tuples for fixed records or composite dict keys; use lists for queues, buffers, and accumulators.

### 8. Can a tuple contain mutable objects? What bug can that cause?

Answer: yes. A tuple prevents replacing its elements, but it does not freeze mutable objects inside it.

```python
t = (["AAPL"], "strategy-a")
t[0].append("MSFT")
```

Bug: treating the tuple as an immutable snapshot while nested state still changes.

### 9. Compare `set` and `dict`. How does hashing affect lookup behavior?

Answer: both are hash-table based. A set stores unique values; a dict stores key-value mappings. Average lookup/insert/delete is O(1), assuming stable hashes and low collision rates. Values used as set members or dict keys must be hashable and should not mutate their hash/equality fields.

### 10. Why should objects used as dict keys not mutate fields involved in equality/hash?

Answer: dicts place keys according to hash and equality. If those change after insertion, the key may live in the wrong bucket and lookups can fail. Use immutable keys like strings, ints, tuples of immutable values, or frozen dataclasses.

### 11. Explain list/set/dict comprehensions. When would you prefer a generator expression?

Answer: comprehensions build collections concisely: lists with `[]`, sets with `{x for ...}`, dicts with `{k: v for ...}`. Prefer a generator expression when streaming into something like `sum`, `any`, or a file parser so you avoid materializing a large intermediate list.

### 12. Compare comprehensions with `map`, `filter`, and `lambda` from a readability perspective.

Answer: comprehensions are usually clearer for simple transformations and filters. `map`/`filter` can be fine with named functions, but complex lambdas are harder to read and debug. In production Python, prefer the form that makes intent obvious.

### 13. What is an iterator? What is `StopIteration`?

Answer: an iterable can produce an iterator with `iter()`. An iterator returns values from `next()` until it is exhausted, then raises `StopIteration`. File handles, cursors, and streaming API responses behave like one-pass iterators.

### 14. What is a generator and how does `yield` help stream large data?

Answer: a generator is a lazy iterator created by a function using `yield`. It keeps local state between yielded values and produces one item at a time, which is useful for large files, logs, and event streams because it avoids loading everything into memory.

### 15. Write a decorator for timing/logging and explain why `functools.wraps` matters.

Answer:

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

`wraps` preserves metadata like function name, docstring, annotations, and framework routing/debugging behavior.

### 16. What is a context manager? How does `__exit__` handle exceptions?

Answer: a context manager runs setup and cleanup around a `with` block using `__enter__` and `__exit__`. `__exit__` runs even if an exception occurs. If it returns `True`, the exception is suppressed; usually return `False` or `None` so failures propagate.

### 17. How should exceptions be logged/re-raised in production services?

Answer: catch specific exceptions, log useful context such as symbol/order/request ID, and preserve the stack trace. Use `raise` to re-raise the same exception or `raise DomainError(...) from exc` to translate while keeping the root cause. Avoid `except Exception: pass`.

### 18. Explain a safe retry pattern. Why are retries dangerous for order submission?

Answer: safe retries need transient-error filtering, backoff, jitter, deadlines, metrics, and idempotency. Order submission is dangerous because a timeout does not prove the order failed; the exchange may have accepted it. Use client order IDs, reconciliation, and an explicit unknown state instead of blindly resubmitting.

### 19. How do `*args` and `**kwargs` work? When are they useful or harmful?

Answer: `*args` captures extra positional arguments; `**kwargs` captures extra keyword arguments. They are useful for decorators, adapters, and forwarding calls. They are harmful when they make public APIs vague, hide required parameters, or weaken type checking.

### 20. Compare `classmethod` and `staticmethod`. When do you use factory methods?

Answer: `classmethod` receives `cls` and is useful for alternative constructors that should preserve subclasses. `staticmethod` receives no implicit object/class and is just a namespaced helper. Use factory classmethods like `Client.from_config(config)` when construction needs parsing or validation.

### 21. Explain inheritance vs composition for exchange connectors.

Answer: inheritance models an `is-a` relationship and can define a common connector interface. Composition builds services from dependencies, such as an `OrderService` holding a connector. For exchange systems, use polymorphism for connector contracts, but prefer composition for business services so dependencies are testable and replaceable.

### 22. Compare threading and multiprocessing for IO-bound and CPU-bound work.

Answer: threads share memory and are useful for IO-bound work because waiting on network/disk can release control. Multiprocessing uses separate processes and can run CPU-bound Python in parallel without the GIL, but adds serialization, startup, and memory overhead.

### 23. What is the GIL? Does it make Python code thread-safe?

Answer: the GIL is CPython's Global Interpreter Lock; it allows only one thread to execute Python bytecode at a time. It limits CPU-bound parallelism in threads, but it does not make application logic thread-safe. Shared mutable state still needs locks, queues, or clear ownership.

### 24. Explain `async`/`await` and how FastAPI benefits from async IO.

Answer: `async def` creates a coroutine, and `await` yields control to the event loop while waiting for IO. FastAPI benefits when handlers use async DB/HTTP clients because one worker can handle many concurrent waits. Blocking calls like `time.sleep()` or sync DB drivers can stall the event loop.

### 25. How do you safely parse JSON and handle large files in backend services?

Answer: parse JSON with `json.loads`, catch `json.JSONDecodeError`, then validate required fields and types. For large files, stream line-by-line or chunk-by-chunk instead of reading the whole file. In financial systems, avoid floats for exact money/price representation when precision matters.

---

## Coding prompts

### 1. Mutable default bug

```python
def add_seen(symbol, seen=[]):
    seen.append(symbol)
    return seen

print(add_seen("AAPL"))
print(add_seen("MSFT"))
```

Answer: the default list is shared across calls. Replace it with a `None` sentinel and create a fresh list per call.

Output from the buggy version:

```text
['AAPL']
['AAPL', 'MSFT']
```

```python
def add_seen(symbol: str, seen: list[str] | None = None) -> list[str]:
    if seen is None:
        seen = []
    seen.append(symbol)
    return seen
```

### 2. Shallow copy bug

```python
base = {"risk": {"checks": []}}
order = base.copy()
order["risk"]["checks"].append("max_qty")
print(base)
```

Answer: `base.copy()` creates a new outer dict but shares the nested `risk` dict and `checks` list. Prefer fresh construction for small objects.

```python
base = {"risk": {"checks": []}}
order = {"risk": {"checks": list(base["risk"]["checks"])}}
order["risk"]["checks"].append("max_qty")

print(base)   # {'risk': {'checks': []}}
print(order)  # {'risk': {'checks': ['max_qty']}}
```

Why: the fixed version creates a fresh nested `checks` list, so `order` can change without mutating `base`. Use `copy.deepcopy` only when the object graph is dynamic and the allocation cost is acceptable.

### 3. Dict key mutation

```python
class Key:
    def __init__(self, symbol):
        self.symbol = symbol
    def __hash__(self):
        return hash(self.symbol)
    def __eq__(self, other):
        return isinstance(other, Key) and self.symbol == other.symbol

k = Key("AAPL")
d = {k: "route"}
k.symbol = "MSFT"
print(d.get(k))
```

Answer: the key's hash/equality changed after insertion, so the dict may not find it in the bucket where it was stored. Use immutable keys.

Output:

```text
None
```

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Key:
    symbol: str

k = Key("AAPL")
d = {k: "route"}

print(d.get(Key("AAPL")))  # route
```

Why: the frozen dataclass cannot be mutated after insertion, so its hash and equality behavior stay stable.

### 4. Async blocking bug

```python
import time

async def handler():
    time.sleep(1)
    return {"ok": True}
```

Answer: `time.sleep(1)` blocks the event loop, preventing other async requests from making progress. Use an async wait/client, or offload blocking work.

```python
import asyncio

async def handler():
    await asyncio.sleep(1)
    return {"ok": True}
```

```python
import asyncio

def blocking_call() -> dict:
    return {"ok": True}

async def handler():
    return await asyncio.to_thread(blocking_call)
```

Why: async code only helps when blocking waits yield control or are moved out of the event loop.

### 5. Retry semantics

```python
def submit_order(order):
    for _ in range(3):
        try:
            return exchange.send(order)
        except TimeoutError:
            continue
```

Answer: dangerous because the order may have reached the exchange even though the client timed out. Blind retry can duplicate orders. Use a stable client order ID, reconcile status, add backoff/metrics, and return an explicit unknown state if reconciliation fails.

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

Why: a timeout leaves the order state unknown. The code uses the client order ID to check whether the exchange already knows the order before trying again.

---

## How to structure answers

```text
Concept -> production problem -> code example -> tradeoff -> safe pattern
```

Example:

```text
Deep copy recursively copies nested objects, which prevents shared nested-state bugs.
But in low-latency systems it can allocate heavily, so I would avoid it in hot paths and prefer explicit object construction or immutable templates.
```
