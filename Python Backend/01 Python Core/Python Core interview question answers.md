# Python Core Interview Question Answers

Tags: #python #core #interview #answers #backend #hft

Use this as the answer key for questions raised across the Python Core notes. Keep answers practical: define the concept, mention the production bug, then give the safe pattern.

---

## Collections And Counting Patterns

### `defaultdict`

**Q: What is the difference between `d[key]` and `d.get(key)` on a `defaultdict`?**

`d[key]` triggers the default factory for a missing key and inserts the new value. `d.get(key)` reads without inserting.

```python
from collections import defaultdict

d = defaultdict(list)

print(d["missing"])      # []
print("missing" in d)    # True

print(d.get("other"))    # None
print("other" in d)      # False
```

Backend relevance: accidental reads like `metrics[user_id]` can create unbounded keys in a long-running process. Use `.get()` when checking presence without mutation.

**Q: Why is `defaultdict(list)` safer than `defaultdict([])`?**

`defaultdict` expects a callable factory. `list` is callable and creates a fresh list per missing key. `[]` is a list object, not a callable, so it is invalid.

```python
from collections import defaultdict

good = defaultdict(list)
good["NASDAQ"].append("order-1")

# bad = defaultdict([])  # TypeError: first argument must be callable or None
```

**Q: When can `defaultdict` cause a memory leak?**

When missing-key reads create keys forever, especially with unbounded identifiers like user IDs, request IDs, symbols from bad input, or generated cache keys.

Safe pattern:

```python
if account_id in balances:
    return balances[account_id]
return None
```

Use bounded caches, TTLs, validation, or `.get()` for non-mutating reads.

---

### `Counter`

**Q: How do you find top-k frequent values?**

Use `Counter(values).most_common(k)`.

```python
from collections import Counter

errors = [500, 429, 500, 404, 500, 429]
print(Counter(errors).most_common(2))
# [(500, 3), (429, 2)]
```

Backend use: top error codes, most rejected symbols, most frequent endpoints, most active accounts during an incident.

**Q: What happens if a `Counter` count becomes zero or negative?**

The key can remain in the `Counter` with zero or negative count. Unary plus removes zero and negative counts.

```python
from collections import Counter

c = Counter({"AAPL": 2})
c["AAPL"] -= 2
c["MSFT"] -= 1

print(c)   # Counter({'AAPL': 0, 'MSFT': -1})
print(+c)  # Counter()
```

**Q: Why is `Counter` usually better than manual dict counting in interview code?**

It is shorter, clearer, less error-prone, and exposes useful operations like `.most_common()`, subtraction, addition, and cleanup.

```python
counts = Counter(row["status"] for row in logs)
```

Manual dict counting is fine when you need custom behavior, but `Counter` communicates intent immediately.

---

## Shallow Copy Vs Deep Copy

**Q: What is the difference between `b = a`, `copy.copy(a)`, and `copy.deepcopy(a)`?**

| Operation | Outer object | Nested objects | Meaning |
|---|---|---|---|
| `b = a` | Same | Same | Alias only |
| `copy.copy(a)` / `a.copy()` | New | Shared | Shallow copy |
| `copy.deepcopy(a)` | New | Recursively copied | Deep copy |

```python
import copy

a = {"risk": {"checks": ["max_qty"]}}

alias = a
shallow = copy.copy(a)
deep = copy.deepcopy(a)

print(alias is a)              # True
print(shallow is a)            # False
print(shallow["risk"] is a["risk"])  # True
print(deep["risk"] is a["risk"])     # False
```

**Q: Why does mutating `b[0]` after `b = a.copy()` sometimes mutate `a`?**

Because `a.copy()` creates a new outer list but shares nested mutable objects.

```python
a = [["AAPL"], ["MSFT"]]
b = a.copy()

b[0].append("NVDA")
print(a)  # [['AAPL', 'NVDA'], ['MSFT']]
```

Safe options: deep copy, immutable nested structures, explicit constructors, or copy only the nested fields you intend to mutate.

**Q: How does `deepcopy` handle cycles?**

`deepcopy` uses an internal memo dictionary to avoid infinite recursion and preserve internal alias relationships.

```python
import copy

a = []
a.append(a)

b = copy.deepcopy(a)
print(b is b[0])  # True
print(b is a)     # False
```

**Q: Why can a tuple still be affected by mutation?**

Tuple immutability is shallow. You cannot reassign tuple slots, but mutable objects inside the tuple can change.

```python
t = (["AAPL"], "strategy-a")
t[0].append("MSFT")
print(t)  # (['AAPL', 'MSFT'], 'strategy-a')
```

Use tuples of immutable values for stable keys/snapshots.

**Q: When would you avoid `deepcopy` in a backend or HFT system?**

Avoid it in hot paths, large object graphs, request loops, message handlers, and latency-sensitive code. It can create CPU cost, memory pressure, GC pressure, and tail-latency spikes.

Prefer:

- Immutable templates.
- Explicit constructors.
- Copy-on-write.
- Narrow copies of only the fields you mutate.
- Ownership discipline instead of defensive copying everywhere.

**Q: How would you safely copy a nested configuration dict?**

If the config is small and plain data, `copy.deepcopy()` is acceptable at a boundary. For production services, prefer typed config objects and explicit copying of mutable fields.

```python
from dataclasses import dataclass, field, replace

@dataclass(frozen=True)
class RiskConfig:
    checks: tuple[str, ...]
    max_qty: int

base = RiskConfig(checks=("max_qty", "price_band"), max_qty=1000)
custom = replace(base, max_qty=500)
```

This avoids hidden shared nested lists.

**Q: What happens when a dataclass is frozen but contains a list?**

`frozen=True` prevents rebinding attributes, but it does not make nested mutable objects immutable.

```python
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Config:
    checks: list[str] = field(default_factory=list)

c = Config()
c.checks.append("max_qty")  # allowed
# c.checks = []             # blocked
```

Use tuples for deep immutability of simple collections.

**Q: Why is returning `self._items` from a class risky?**

It exposes internal mutable state. Callers can mutate the object without validation, logging, locking, or invariants.

```python
class Book:
    def __init__(self):
        self._orders = []

    def orders(self) -> tuple[str, ...]:
        return tuple(self._orders)
```

Return an immutable snapshot, iterator, or controlled copy.

**Q: How can shallow copies create concurrency bugs?**

Two threads/tasks may think they own separate objects, but nested mutable state is shared.

```python
template = {"headers": {"x-service": "orders"}}
req_a = template.copy()
req_b = template.copy()

req_a["headers"]["x-request-id"] = "req-a"
print(req_b["headers"]["x-request-id"])  # leaked shared nested state
```

In concurrent backends, this can leak auth headers, request IDs, risk settings, or cached state between requests.

**Q: What kinds of objects should not be deep-copied?**

Avoid deep-copying resources with identity/lifecycle:

- Sockets.
- Files.
- Locks.
- DB sessions/connections.
- Thread/process pools.
- Generators.
- Open HTTP clients.
- Objects wrapping external handles.

Create new resources through explicit constructors or dependency lifecycle management.

---

## Mutability And Object Semantics

**Q: Is assignment a copy in Python?**

No. Assignment binds a name to an object.

```python
a = [1, 2]
b = a
b.append(3)
print(a)  # [1, 2, 3]
```

Backend relevance: passing a request/config/list around can share mutable ownership unless you copy or define clear ownership.

**Q: Are tuples always immutable and safe?**

Tuples are top-level immutable only. They are safe as dict keys only if every element is hashable and hash-stable.

```python
good_key = ("NASDAQ", "AAPL")
bad_key = ("NASDAQ", ["AAPL"])

print(hash(good_key))
# hash(bad_key)  # TypeError
```

**Q: When should you use `is` vs `==`?**

Use `is` for identity and singletons like `None`. Use `==` for value equality.

```python
if timeout is None:
    timeout = 1.0

if status == "FILLED":
    handle_fill()
```

Do not rely on small-int or string interning.

**Q: Why are mutable default arguments dangerous?**

Defaults are evaluated once at function definition time, so mutable defaults are shared across calls.

```python
def add_error(code: int, errors: list[int] | None = None) -> list[int]:
    if errors is None:
        errors = []
    errors.append(code)
    return errors
```

This prevents cross-request or cross-test state leakage.

**Q: Are immutable objects automatically thread-safe?**

Immutable objects are safe to share because their value cannot change in place. But a program using immutable objects can still have races around rebinding, check-then-act logic, database state, or external side effects.

Use locks, queues, transactions, single-writer ownership, or atomic database updates for shared mutable state.

---

## Strong Interview Answer Patterns

### Copying / Mutability

```text
Assignment aliases the same object.
Shallow copy copies only the outer container.
Deep copy recursively copies the object graph.
The production risk is shared nested mutable state.
I avoid blind deepcopy in hot paths and prefer explicit ownership or immutable structures.
```

### Collections

```text
I use defaultdict for grouping, deque for O(1) queue/sliding-window operations,
and Counter for frequency/top-k problems. The main production pitfall is unbounded
state growth in long-running services.
```

### Backend/HFT Framing

```text
In backend services, Python object semantics matter because processes are long-lived.
Shared mutable state can leak between requests, workers, retries, or exchange messages.
In latency-sensitive systems, unnecessary deep copies and allocations can show up as p99 spikes.
```

---

## Quick Revision

- `d[key]` mutates a `defaultdict` on miss; `.get()` does not.
- `Counter.most_common(k)` is the clean top-k answer.
- `b = a` aliases; shallow copy shares nested objects; deep copy recursively copies.
- Tuples/frozen dataclasses are only shallowly immutable if they contain mutables.
- Never rely on `is` for value comparison.
- Avoid mutable defaults.
- Do not deep-copy sockets, DB sessions, locks, pools, or live clients.
- Prefer explicit ownership, immutable snapshots, and narrow copies in production code.
