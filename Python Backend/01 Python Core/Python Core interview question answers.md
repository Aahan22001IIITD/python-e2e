# Python Core Interview Question Answers

Tags: #python #core #interview #answers #backend #hft

Use this as a short answer key for the Python Core notes. Each answer should define the idea, show the code/output, and explain the practical reason.

---

## Collections and counting patterns

### What is the difference between `d[key]` and `d.get(key)` on a `defaultdict`?

`d[key]` creates and inserts a default value when the key is missing. `d.get(key)` checks without inserting.

```python
from collections import defaultdict

d = defaultdict(list)

print(d["missing"])
print("missing" in d)

print(d.get("other"))
print("other" in d)
```

Output:

```text
[]
True
None
False
```

Why: `defaultdict(list)` calls `list()` for `"missing"`, stores that list, and returns it. `.get("other")` does not call the factory.

Keep in mind: use `.get()` or `key in d` for non-mutating reads in long-running services.

### Why use `defaultdict(list)` instead of `defaultdict([])`?

`defaultdict` needs a callable factory. `list` is callable and creates a new list. `[]` is already a list object, so it is not valid.

```python
from collections import defaultdict

good = defaultdict(list)
good["NASDAQ"].append("order-1")

print(good["NASDAQ"])
```

Output:

```text
['order-1']
```

Why: the first access to `"NASDAQ"` calls `list()` and gives that key its own empty list.

### How do you find top-k frequent values?

Use `Counter(values).most_common(k)`.

```python
from collections import Counter

errors = [500, 429, 500, 404, 500, 429]
print(Counter(errors).most_common(2))
```

Output:

```text
[(500, 3), (429, 2)]
```

Why: `Counter` counts each error code, and `most_common(2)` returns the two highest counts.

### What happens if a `Counter` count becomes zero or negative?

The key can remain in the `Counter`. Unary plus removes zero and negative counts.

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

Why: `Counter` supports subtraction, so it does not automatically delete non-positive counts.

---

## Copying and mutability

### What is the difference between assignment, shallow copy, and deep copy?

| Operation | Outer object | Nested objects | Meaning |
| --- | --- | --- | --- |
| `b = a` | Same | Same | Alias only |
| `copy.copy(a)` / `a.copy()` | New | Shared | Shallow copy |
| `copy.deepcopy(a)` | New | Recursively copied | Deep copy |

```python
import copy

a = {"risk": {"checks": ["max_qty"]}}

alias = a
shallow = copy.copy(a)
deep = copy.deepcopy(a)

print(alias is a)
print(shallow is a)
print(shallow["risk"] is a["risk"])
print(deep["risk"] is a["risk"])
```

Output:

```text
True
False
True
False
```

Why: assignment creates another name for the same object. A shallow copy creates only a new outer dict. A deep copy also copies the nested dict/list.

### Why can mutating a shallow copy also mutate the original?

Because nested mutable objects are still shared.

```python
a = [["AAPL"], ["MSFT"]]
b = a.copy()

b[0].append("NVDA")
print(a)
```

Output:

```text
[['AAPL', 'NVDA'], ['MSFT']]
```

Why: `b` has a new outer list, but `b[0]` and `a[0]` point to the same inner list.

Keep in mind: copy only the nested fields you plan to mutate, or use immutable nested structures.

### When would you avoid `deepcopy`?

Avoid repeated `deepcopy` in hot paths, large object graphs, request loops, and message handlers. It can add CPU cost, memory pressure, and latency spikes.

Prefer immutable templates, explicit constructors, copy-on-write, or narrow copies of only the fields you mutate.

### What kinds of objects should not be deep-copied?

Do not deep-copy resources with identity or lifecycle: sockets, files, locks, DB sessions, thread pools, generators, open HTTP clients, or objects wrapping external handles.

Why: these objects represent live external state. Create them through explicit lifecycle management instead.

---

## Object semantics

### Is assignment a copy in Python?

No. Assignment binds a name to an object.

```python
a = [1, 2]
b = a
b.append(3)
print(a)
```

Output:

```text
[1, 2, 3]
```

Why: `a` and `b` point to the same list.

### Are tuples always safe immutable records?

No. Tuples are immutable only at the top level. A tuple can still contain a mutable object.

```python
t = (["AAPL"], "strategy-a")
t[0].append("MSFT")
print(t)
```

Output:

```text
(['AAPL', 'MSFT'], 'strategy-a')
```

Why: the tuple slot still points to the same list, and the list can change.

Keep in mind: use tuples of immutable values for stable keys and snapshots.

### When should you use `is` vs `==`?

Use `is` for identity and singletons like `None`. Use `==` for value equality.

```python
timeout = None
status = "FILLED"

print(timeout is None)
print(status == "FILLED")
```

Output:

```text
True
True
```

Why: `None` is a singleton, so identity is the right check. `"FILLED"` is a value, so equality is the right check.

### Why are mutable default arguments dangerous?

Defaults are evaluated once at function definition time, so a mutable default is shared across calls.

```python
def add_error(code: int, errors: list[int] = []) -> list[int]:
    errors.append(code)
    return errors


print(add_error(500))
print(add_error(429))
```

Output:

```text
[500]
[500, 429]
```

Why: both calls reuse the same `errors` list.

Safe version:

```python
def add_error(code: int, errors: list[int] | None = None) -> list[int]:
    if errors is None:
        errors = []
    errors.append(code)
    return errors
```

### Are immutable objects automatically thread-safe?

Immutable objects are safe to share because their value cannot change in place. The program can still have races around rebinding, check-then-act logic, database writes, or external side effects.

Use locks, queues, transactions, single-writer ownership, or atomic database updates for shared mutable state.

---

## Strong answer patterns

Copying/mutability:

```text
Assignment aliases the same object.
Shallow copy copies only the outer container.
Deep copy recursively copies nested objects.
The production risk is shared mutable state.
In hot paths, I prefer explicit ownership or immutable structures over blind deepcopy.
```

Collections:

```text
I use defaultdict for grouping, deque for queues/sliding windows,
and Counter for frequency or top-k problems.
The main service risk is unbounded state growth from accidental keys.
```

Backend framing:

```text
Python object semantics matter because backend processes are long-lived.
Shared mutable state can leak between requests, workers, retries, or messages.
Unnecessary copies can also affect p99 latency in hot paths.
```

---

## Quick revision

- `d[key]` inserts on a missing `defaultdict` key; `.get()` does not.
- `Counter.most_common(k)` is the clean top-k answer.
- `b = a` aliases; shallow copy shares nested objects; deep copy recursively copies.
- Tuples and frozen dataclasses are shallowly immutable if they contain mutables.
- Use `is` for `None` and `==` for normal values.
- Avoid mutable defaults.
- Do not deep-copy sockets, DB sessions, locks, pools, or live clients.
- Prefer explicit ownership, immutable snapshots, and narrow copies in production code.
