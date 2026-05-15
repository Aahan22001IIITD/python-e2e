# Collections and counting patterns

Tags: #python #collections #defaultdict #deque #counter #backend #hft

Use `collections` when the data structure says what the code is doing. These tools are common in grouping, queues, sliding windows, frequency counts, and log analysis.

---

## Practical overview

| Tool | Use when | Backend example |
| --- | --- | --- |
| `defaultdict` | Missing keys should create a default value | group orders by venue |
| `deque` | Need fast append/pop from both ends | queue or rolling window |
| `Counter` | Need frequencies or top-k values | most common error codes |
| `namedtuple` / `dataclass` | Need a lightweight record | market data event |
| `OrderedDict` | Need ordered map behavior | simple cache/LRU logic |
| `ChainMap` | Need layered lookup | env config over defaults |

---

## `defaultdict`

`defaultdict(factory)` calls `factory()` when a missing key is accessed with `d[key]`. It is useful when every missing key should start with the same kind of empty value.

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

Output:

```text
[{'id': '1', 'venue': 'NASDAQ', 'symbol': 'AAPL'}, {'id': '3', 'venue': 'NASDAQ', 'symbol': 'MSFT'}]
```

Why: `defaultdict(list)` creates a fresh empty list for each new venue, then the order is appended to that list.

Counting can also use `defaultdict(int)`:

```python
from collections import defaultdict

counts = defaultdict(int)
for code in [200, 500, 200, 429]:
    counts[code] += 1

print(dict(counts))
```

Output:

```text
{200: 2, 500: 1, 429: 1}
```

Why: `int()` returns `0`, so the first `+= 1` works even when the key is new.

`d[key]` and `d.get(key)` behave differently on missing keys:

```python
from collections import defaultdict

groups = defaultdict(list)

print(groups["missing"])
print("missing" in groups)

print(groups.get("other"))
print("other" in groups)
```

Output:

```text
[]
True
None
False
```

Why: `groups["missing"]` inserts a new list. `groups.get("other")` reads without inserting.

Keep in mind: accidental reads can grow state in a long-running process. Use `.get()` or `key in d` when you only want to check.

---

## `deque`

`deque` is a double-ended queue. Appending or popping from either end is O(1), so it fits queues and rolling windows better than a list with `pop(0)`.

```python
from collections import deque

q = deque()
q.append("msg-1")
q.append("msg-2")

print(q.popleft())
print(q.popleft())
```

Output:

```text
msg-1
msg-2
```

Why: `popleft()` removes from the front without shifting every remaining element.

`deque(maxlen=N)` keeps only the latest `N` items:

```python
from collections import deque

prices = deque(maxlen=3)

for price in [100.0, 101.0, 99.5, 102.0]:
    prices.append(price)
    print(list(prices), round(sum(prices) / len(prices), 2))
```

Output:

```text
[100.0] 100.0
[100.0, 101.0] 100.5
[100.0, 101.0, 99.5] 100.17
[101.0, 99.5, 102.0] 100.83
```

Why: once the deque reaches `maxlen=3`, adding a new item automatically drops the oldest item.

| Operation | `list` | `deque` |
| --- | --- | --- |
| Append right | Amortized O(1) | O(1) |
| Pop right | O(1) | O(1) |
| Pop left | O(n) | O(1) |
| Random access | O(1) | O(n) |

Keep in mind: `deque` is great for ends, not for heavy random indexing.

---

## `Counter`

`Counter` counts how many times each value appears. It is a dict subclass, so keys are the values being counted and values are the counts.

```python
from collections import Counter

symbols = ["AAPL", "MSFT", "AAPL", "NVDA", "AAPL", "MSFT"]
counts = Counter(symbols)

print(counts["AAPL"])
print(counts.most_common(2))
```

Output:

```text
3
[('AAPL', 3), ('MSFT', 2)]
```

Why: `Counter` scans the iterable and increments the count for each symbol. `.most_common(2)` returns the two highest counts.

Log-style example:

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

Output:

```text
[(500, 2), (200, 1), (429, 1)]
```

Why: the generator pulls only the `status` field from each log row, then `Counter` aggregates those statuses.

Counts can be zero or negative:

```python
from collections import Counter

c = Counter({"AAPL": 2})
c["AAPL"] -= 2
c["MSFT"] -= 1

print(c)
print(+c)
```

Output:

```text
Counter({'AAPL': 0, 'MSFT': -1})
Counter()
```

Why: `Counter` keeps zero and negative counts until you clean it. Unary `+c` returns a new counter with only positive counts.

Keep in mind: `Counter` is usually clearer than manual dict counting. Use manual counting only when the update logic is custom.

---

## Quick revision

- Use `defaultdict(list)` for grouping and `defaultdict(int)` for simple counting.
- `d[key]` inserts on a missing `defaultdict` key; `.get()` does not.
- Use `deque` for queues and sliding windows.
- Avoid `list.pop(0)` in hot paths.
- Use `Counter(values).most_common(k)` for top-k frequency questions.
- Clean zero or negative `Counter` values with unary `+` when needed.
