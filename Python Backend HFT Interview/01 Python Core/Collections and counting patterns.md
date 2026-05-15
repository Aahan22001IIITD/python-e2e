 # Collections and counting patterns

Tags: #python #collections #defaultdict #deque #counter #backend #hft

Use `collections` when the data structure expresses intent better than manual dict/list code. In interviews, these often appear in log processing, queues, sliding windows, frequency counts, and streaming systems.

---

## Practical overview

| Tool                       | Use when                                     | Backend/HFT example             |
| -------------------------- | -------------------------------------------- | ------------------------------- |
| `defaultdict`              | Missing keys should initialize automatically | group orders by venue           |
| `deque`                    | Fast append/pop from both ends               | rolling window, in-memory queue |
| `Counter`                  | Frequency counts and top-k                   | most common error codes/symbols |
| `namedtuple` / `dataclass` | Lightweight records                          | market data event shape         |
| `OrderedDict`              | Ordered map / simple LRU patterns            | legacy or custom cache behavior |
| `ChainMap`                 | Layered config lookup                        | env overrides over defaults     |

---

## `defaultdict`

### Concept

`defaultdict(factory)` calls `factory()` when a missing key is accessed.

Why backend systems care:

- Avoids repetitive `if key not in d` code.
- Useful for grouping, aggregating, counting, routing, and metrics buckets.
- Mistake: reading a missing key creates it, which can grow state unexpectedly.

### Runnable examples

Grouping orders by venue:

```python
from collections import defaultdict

orders = [
    {"id": "1", "venue": "NASDAQ", "symbol": "AAPL"},
    {"id": "2", "venue": "NYSE", "symbol": "IBM"},
    {"id": "3", "venue": "NASDAQ", "symbol": "MSFT"},
]

by_venue: defaultdict[str, list[dict]] = defaultdict(list)

for order in orders:
    by_venue[order["venue"]].append(order)

print(by_venue["NASDAQ"])
```

Counting without `Counter`:

```python
from collections import defaultdict

counts = defaultdict(int)
for code in [200, 500, 200, 429]:
    counts[code] += 1

print(dict(counts))  # {200: 2, 500: 1, 429: 1}
```

Edge case:

```python
from collections import defaultdict

groups = defaultdict(list)
print(groups["missing"])  # [] and key now exists
print("missing" in groups)  # True

# Use `.get()` when you do not want insertion:
print(groups.get("another_missing"))  # None
```

### Interview traps/questions

- What is the difference between `d[key]` and `d.get(key)` on a `defaultdict`?

  Answer: `d[key]` triggers the default factory on a missing key and inserts the generated value. `d.get(key)` reads without inserting.

  ```python
  from collections import defaultdict

  groups = defaultdict(list)
  print(groups["missing"])      # [] and key is inserted
  print("missing" in groups)    # True

  print(groups.get("other"))    # None and no insertion
  print("other" in groups)      # False
  ```

- Why is `defaultdict(list)` safer than `defaultdict([])`?

  Answer: `defaultdict` expects a callable factory. `list` is callable and creates a fresh list for each missing key. `[]` is a list object, not a callable.

  ```python
  from collections import defaultdict

  by_venue = defaultdict(list)
  by_venue["NASDAQ"].append("order-1")

  # bad = defaultdict([])  # TypeError
  ```

- When can `defaultdict` cause a memory leak?

  Answer: when accidental reads create endless keys in a long-running process, especially with unbounded request IDs, user IDs, symbols, or bad input. Use `.get()` or membership checks for non-mutating reads.

  ```python
  if account_id in balances:
      return balances[account_id]
  return None
  ```

### Quick revision

- `defaultdict` reduces boilerplate for grouping/counting.
- Missing-key access inserts a value.
- Use `.get()` for non-mutating reads.
- In long-running services, guard unbounded key growth.

---

## `deque`

### Concept

`deque` is a double-ended queue with O(1) append/pop from both ends.

Why backend systems care:

- Sliding windows for rate limits, rolling metrics, recent ticks.
- Lightweight producer/consumer queues inside one process.
- Avoids O(n) `list.pop(0)`.

### Runnable examples

Queue behavior:

```python
from collections import deque

q = deque()
q.append("msg-1")
q.append("msg-2")

print(q.popleft())  # msg-1
print(q.popleft())  # msg-2
```

Sliding window:

```python
from collections import deque

prices = deque(maxlen=3)

for price in [100.0, 101.0, 99.5, 102.0]:
    prices.append(price)
    print(list(prices), sum(prices) / len(prices))

# maxlen automatically drops oldest items.
```

Rate-limit sketch:

```python
from collections import deque
import time

events = deque()

def allow(max_events: int, window_sec: float) -> bool:
    now = time.monotonic()
    while events and now - events[0] > window_sec:
        events.popleft()
    if len(events) >= max_events:
        return False
    events.append(now)
    return True
```

### Performance

| Operation | `list` | `deque` |
| --- | --- | --- |
| Append right | Amortized O(1) | O(1) |
| Pop right | O(1) | O(1) |
| Pop left | O(n) | O(1) |
| Random access | O(1) | O(n) |

### Quick revision

- Use `deque` for queues and sliding windows.
- Avoid `list.pop(0)` in hot paths.
- `deque(maxlen=N)` is useful for bounded recent history.
- Do not use `deque` for heavy random indexing.

---

## `Counter`

### Concept

`Counter` is a dict subclass for frequency counting.

Why backend systems care:

- Summarize logs, error codes, user agents, symbols, venue rejects.
- Useful for top-k interview problems and incident analysis.

### Runnable examples

```python
from collections import Counter

symbols = ["AAPL", "MSFT", "AAPL", "NVDA", "AAPL", "MSFT"]
counts = Counter(symbols)

print(counts["AAPL"])        # 3
print(counts.most_common(2)) # [('AAPL', 3), ('MSFT', 2)]
```

Log processing:

```python
from collections import Counter

logs = [
    {"status": 200, "path": "/orders"},
    {"status": 500, "path": "/orders"},
    {"status": 429, "path": "/orders"},
    {"status": 500, "path": "/fills"},
]

status_counts = Counter(row["status"] for row in logs)
print(status_counts.most_common())
```

Edge cases:

```python
from collections import Counter

c = Counter({"ok": 3})
c["ok"] -= 5
print(c)  # Counter({'ok': -2})

print(+c)  # Counter() removes zero/negative counts
```

### Interview traps/questions

- How do you find top-k frequent values?

  Answer: use `Counter(values).most_common(k)`.

  ```python
  from collections import Counter

  errors = [500, 429, 500, 404, 500, 429]
  print(Counter(errors).most_common(2))
  # [(500, 3), (429, 2)]
  ```

- What happens if a `Counter` count becomes zero or negative?

  Answer: the key can remain in the `Counter` with zero or negative count. Unary plus removes zero and negative counts.

  ```python
  from collections import Counter

  c = Counter({"AAPL": 2})
  c["AAPL"] -= 2
  c["MSFT"] -= 1

  print(c)   # Counter({'AAPL': 0, 'MSFT': -1})
  print(+c)  # Counter()
  ```

- Why is `Counter` usually better than manual dict counting in interview code?

  Answer: it is shorter, clearer, less error-prone, and has built-in operations like `.most_common()`, addition, subtraction, and cleanup. Manual counting is fine only when custom behavior is needed.

### Quick revision

- `Counter(iterable)` counts values.
- `.most_common(k)` solves top-k frequency tasks.
- Counts can be zero or negative.
- Use generators with `Counter` for memory-efficient log scanning.
