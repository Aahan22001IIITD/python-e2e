# Coding exercises

Tags: #python #coding-practice #interview #backend #hft

Small runnable exercises for quick revision. Try writing each from memory, then compare with the solution.

---

## 1. Fix mutable default state

Prompt:

```python
def add_error(code, errors=[]):
    errors.append(code)
    return errors
```

Solution:

```python
def add_error(code: int, errors: list[int] | None = None) -> list[int]:
    if errors is None:
        errors = []
    errors.append(code)
    return errors
```

Expected behavior:

```python
print(add_error(400))
print(add_error(500))
```

Output:

```text
[400]
[500]
```

Why: using `None` creates a fresh list for each call that does not pass `errors`. Keep in mind: mutable defaults are evaluated once at function definition time.

---

## 2. Group orders by venue

Prompt: Given a list of orders, group them by venue.

```python
orders = [
    {"id": "1", "venue": "NASDAQ"},
    {"id": "2", "venue": "NYSE"},
    {"id": "3", "venue": "NASDAQ"},
]
```

Solution:

```python
from collections import defaultdict

by_venue = defaultdict(list)
for order in orders:
    by_venue[order["venue"]].append(order)

print(dict(by_venue))
```

Output:

```text
{'NASDAQ': [{'id': '1', 'venue': 'NASDAQ'}, {'id': '3', 'venue': 'NASDAQ'}], 'NYSE': [{'id': '2', 'venue': 'NYSE'}]}
```

Why: `defaultdict(list)` creates the list the first time a venue is seen, so the loop can append directly.

---

## 3. Sliding window average

Prompt: Maintain the average of the last N prices.

```python
from collections import deque

class MovingAverage:
    def __init__(self, size: int):
        self.values = deque(maxlen=size)
        self.total = 0.0

    def add(self, value: float) -> float:
        if len(self.values) == self.values.maxlen:
            self.total -= self.values[0]
        self.values.append(value)
        self.total += value
        return self.total / len(self.values)

ma = MovingAverage(3)
for price in [100.0, 101.0, 99.0, 102.0]:
    print(ma.add(price))
```

Output:

```text
100.0
100.5
100.0
100.66666666666667
```

Why: `deque(maxlen=N)` drops the oldest value automatically. Keep in mind: subtract the old value before appending the new one, otherwise the running total becomes wrong.

---

## 4. Top-k symbols

Prompt: Find the two most frequent symbols.

```python
from collections import Counter

symbols = ["AAPL", "MSFT", "AAPL", "NVDA", "AAPL", "MSFT"]
print(Counter(symbols).most_common(2))
```

Output:

```text
[('AAPL', 3), ('MSFT', 2)]
```

Why: `Counter` counts occurrences and `most_common(k)` returns the highest-frequency items without writing sorting/counting code manually.

---

## 5. Safe JSON parser

Prompt: Parse an order JSON string and validate required fields.

```python
import json

def parse_order(raw: str) -> dict:
    try:
        order = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON") from exc

    if "symbol" not in order or "qty" not in order:
        raise ValueError("missing required fields")
    if not isinstance(order["qty"], int) or order["qty"] <= 0:
        raise ValueError("qty must be positive int")
    return order

print(parse_order('{"symbol": "AAPL", "qty": 100}'))
```

Output:

```text
{'symbol': 'AAPL', 'qty': 100}
```

Why: parsing only proves the string is valid JSON; validation proves the payload has the fields and types your service expects.

---

## 6. Timing decorator

Prompt: Write a decorator that logs elapsed time and preserves function metadata.

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

@timed
def normalize(symbol: str) -> str:
    return symbol.strip().upper()

print(normalize(" aapl "))
```

Output shape:

```text
normalize took <elapsed>ms
AAPL
```

Why: the decorator logs elapsed time without changing the function result. Keep in mind: `functools.wraps` preserves metadata used by debuggers, docs, and web frameworks.

---

## 7. Retry with exception chaining

Prompt: Retry only timeout failures and preserve root cause.

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
    raise RuntimeError("timed out after retries") from last_error
```

Why: only `TimeoutError` is retried, and the final exception keeps the original timeout as the root cause. Keep in mind: real production retries also need idempotency, jitter, deadlines, and metrics.

---

## 8. Async gather with timeout

Prompt: Fetch quotes concurrently and bound wait time.

```python
import asyncio

async def quote(symbol: str) -> str:
    await asyncio.sleep(0.05)
    return f"{symbol}=100.0"

async def main():
    tasks = [asyncio.wait_for(quote(s), timeout=0.2) for s in ["AAPL", "MSFT"]]
    print(await asyncio.gather(*tasks))

asyncio.run(main())
```

Output:

```text
['AAPL=100.0', 'MSFT=100.0']
```

Why: both quote requests wait concurrently instead of one after another. Keep in mind: async helps IO concurrency; still add timeouts and backpressure.

---

## 9. Iterator exhaustion

Prompt: Explain output.

```python
it = iter([1, 2, 3])
print(list(it))
print(list(it))
```

Answer:

```text
[1, 2, 3]
[]
```

Why: `list(it)` consumes the iterator the first time, so the second conversion has no remaining values. Keep in mind: file handles, DB cursors, and streaming responses often behave the same way.

---

## 10. Shallow copy production bug

Prompt: Fix the nested mutation issue.

```python
import copy

BASE = {"risk": {"checks": ["max_qty"]}}

def build_order(symbol: str) -> dict:
    order = copy.deepcopy(BASE)
    order["symbol"] = symbol
    order["risk"]["checks"].append("symbol_allowed")
    return order
```

Alternative for hot paths:

```python
def build_order_fast(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "risk": {"checks": ["max_qty", "symbol_allowed"]},
    }
```

Expected output shape:

```python
print(build_order_fast("AAPL"))
```

```text
{'symbol': 'AAPL', 'risk': {'checks': ['max_qty', 'symbol_allowed']}}
```

Why: explicit construction avoids nested shared state and avoids the allocation cost of copying a larger object graph. Keep in mind: deep copy is safe for isolation, but not always the best production design.
