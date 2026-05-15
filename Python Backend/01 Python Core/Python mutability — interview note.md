# Python: mutable vs immutable

Tags: #python #memory-model #concurrency #interview

This note explains mutability in simple backend terms: what changes in place, what creates a new object, and why shared objects can cause bugs.

---

## Definitions

| Concept | Meaning |
| --- | --- |
| Immutable | The object's value cannot change in place. A "change" creates or points to another object. |
| Mutable | The object's contents can change in place. Other names pointing to it see the change. |
| Identity | `x is y`: both names point to the same object. |
| Equality | `x == y`: both objects have the same value. |

Common immutable built-ins: `int`, `float`, `bool`, `str`, `bytes`, `tuple` of immutable values, `frozenset`, `None`.

Common mutable built-ins: `list`, `dict`, `set`, `bytearray`, and most normal class instances.

Key idea: Python variables are names bound to objects. The variable itself is not mutable or immutable; the object is.

---

## Assignment and mutation

Assignment does not copy. It gives another name to the same object unless you explicitly create a copy.

```python
a = [1, 2]
b = a
b.append(3)

print(a)
print(a is b)
```

Output:

```text
[1, 2, 3]
True
```

Why: `a` and `b` point to the same list. Mutating the list through `b` is visible through `a`.

Immutable values behave differently:

```python
s = "hi"
t = s
s += "!"

print(s)
print(t)
print(s is t)
```

Output:

```text
hi!
hi
False
```

Why: strings are immutable, so `s += "!"` creates a new string and rebinds `s`. `t` still points to the old string.

Keep in mind: use explicit copies only when you need isolation. Copying everything by default can make code slower and harder to reason about.

---

## Function arguments

Python passes object references by assignment. A function can mutate a mutable object it receives, but rebinding a local name does not change the caller's name.

```python
def bump(n: int) -> None:
    n = n + 1


def bump_list(xs: list[int]) -> None:
    xs.append(1)


count = 10
items = [10]

bump(count)
bump_list(items)

print(count)
print(items)
```

Output:

```text
10
[10, 1]
```

Why: `bump` only rebinds local `n`. `bump_list` mutates the list object that `items` also points to.

---

## Mutable default arguments

Default arguments are evaluated once when the function is defined. If the default is a list or dict, all calls share it.

```python
def append_one(item, bag=[]):
    bag.append(item)
    return bag


print(append_one(1))
print(append_one(2))
```

Output:

```text
[1]
[1, 2]
```

Why: both calls reuse the same default `bag` list.

Use `None` and create a fresh list:

```python
def append_one(item, bag=None):
    if bag is None:
        bag = []
    bag.append(item)
    return bag
```

Keep in mind: this is a common source of flaky tests and cross-request state leaks in long-running backend workers.

---

## Strings vs lists

Strings are immutable. Lists are mutable.

| Operation | `str` | `list` |
| --- | --- | --- |
| Change one element | No | Yes |
| Build many parts | Use `"".join(parts)` | Use `append` |
| Hashable | Yes | No |
| Dict key | Yes | No |

```python
parts = ["order", "-", "123"]

s = ""
for chunk in parts:
    s += chunk

joined = "".join(parts)

print(s)
print(joined)
```

Output:

```text
order-123
order-123
```

Why: both produce the same string, but repeated `+=` creates intermediate strings. `join` builds the final string more directly.

Keep in mind: for small strings clarity matters more. In loops or hot paths, prefer collecting parts and joining once.

---

## Tuples containing mutable objects

A tuple prevents replacing its slots, but it does not freeze mutable objects inside it.

```python
t = ([1], 2)
t[0].append(2)

print(t)
```

Output:

```text
([1, 2], 2)
```

Why: the tuple still points to the same inner list, and that list can be mutated.

Hashability also depends on every element:

```python
good_key = ("NASDAQ", "AAPL")
bad_key = ("NASDAQ", ["AAPL"])

print(isinstance(hash(good_key), int))
```

Output:

```text
True
```

Why: `good_key` contains only hashable values. `bad_key` cannot be used as a dict key because it contains a list.

Keep in mind: use tuples of immutable values for dict keys, cache keys, and stable records.

---

## `is` vs `==`

`is` checks identity. `==` checks value.

```python
x = [1, 2]
y = [1, 2]

print(x == y)
print(x is y)
```

Output:

```text
True
False
```

Why: the lists have the same contents but are different objects.

Use `is` for `None`:

```python
timeout = None

print(timeout is None)
```

Output:

```text
True
```

Why: `None` is a singleton, so identity is the correct check.

Keep in mind: small integers and some strings may be reused by CPython internally. Do not use `is` for normal value comparison.

---

## Frozen dataclasses

`frozen=True` prevents assigning a new value to a field. It does not make nested mutable objects immutable.

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Config:
    checks: list[str] = field(default_factory=list)


c = Config()
c.checks.append("max_qty")

print(c.checks)
```

Output:

```text
['max_qty']
```

Why: `c.checks = []` would be blocked, but mutating the existing list is still allowed.

Use tuples when you want a simple deeply immutable collection:

```python
@dataclass(frozen=True)
class SafeConfig:
    checks: tuple[str, ...]
```

---

## Performance notes

Immutable "changes" create new objects. Mutable changes can update existing objects. Neither is always better; choose based on the data model and the code path.

```python
parts = ["a", "b", "c"]

slow_style = ""
for part in parts:
    slow_style += part

fast_style = "".join(parts)

print(slow_style == fast_style)
```

Output:

```text
True
```

Why: repeated string concatenation may allocate many intermediate strings. `join` builds the result once from the collected parts.

Keep in mind: in request loops, parsers, and low-latency paths, repeated allocation and unnecessary deep copies can show up in tail latency.

---

## Threading and concurrency

The GIL does not make multi-step business logic safe. Shared mutable state still needs ownership or synchronization.

```python
import threading

limits = {"AAPL": 100}
lock = threading.Lock()


def update_limit(symbol: str, value: int) -> None:
    with lock:
        limits[symbol] = value
```

Why: the lock makes the update section explicit. Without a clear owner or lock, multiple threads can read and write shared dict/list state in unexpected orders.

For multiprocessing, each process usually has separate memory. Mutating an object in a child process does not update the parent's normal Python object unless you use shared memory or a managed proxy.

---

## Common production bugs

| Pattern | Failure mode |
| --- | --- |
| Mutable default args | State leaks between calls or tests |
| Module-level mutable caches | Cross-request bleed in long-running workers |
| Shallow copy of nested config | One component mutates another component's data |
| Returning `self._items` directly | Caller mutates internal state |
| Check-then-act on shared dict/list/set | Race between the check and the update |
| Holding references in logs or callbacks | Large mutable graphs stay alive longer than expected |

Safer patterns: return `tuple(self._items)`, copy at boundaries, document ownership, use immutable values for snapshots, and use locks or queues for shared mutable state.

---

## Quick revision summary

- Immutable objects cannot change in place; mutable objects can.
- Assignment shares references; it does not copy.
- Mutable defaults are shared across calls, so use `None` plus a fresh object.
- Tuple immutability is shallow if it contains mutable objects.
- Use `==` for values and `is` for `None`/singletons.
- Use `join` for building strings from many parts.
- Hash keys must stay stable.
- The GIL does not make multi-step shared-state logic safe.

---

## See also

- [[Interview]]
- [[Welcome]]
