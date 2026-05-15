# Core object semantics

Tags: #python #mutability #copying #identity #hashing #backend #hft

This note covers the Python object-model questions that show up in backend/HFT interviews because they directly affect bugs in request handling, exchange connectors, config objects, caches, and concurrent services.

See also: [[Python mutability — interview note]], [[Python shallow copy vs deep copy]], [[Concurrency GIL async and multiprocessing]]

---

## Mutable vs immutable

### Concept

Python variables are names bound to objects. Mutability is about whether the object can change in place.

| Category  | Examples                                                                                 | Behavior                                |
| --------- | ---------------------------------------------------------------------------------------- | --------------------------------------- |
| Immutable | `int`, `float`, `bool`, `str`, `bytes`, `tuple` of immutable values, `frozenset`, `None` | Operations create/rebind to new objects |
| Mutable   | `list`, `dict`, `set`, `bytearray`, most class instances                                 | Object can be changed in place          |

Why backend systems care:

- Shared mutable request/config state can leak between requests or tasks.
- Mutable globals create cross-request bugs in long-running workers.
- Accidental mutation is hard to detect from logs because identity stays the same while contents change.

### Runnable examples

```python
def mutate_list(xs: list[int]) -> None:
    xs.append(99)

def rebind_int(n: int) -> None:
    n += 1  # local name now points to a new int

orders = [1, 2]
mutate_list(orders)
print(orders)  # [1, 2, 99]

count = 10
rebind_int(count)
print(count)  # 10
```

Memory/reference diagram:

```text
orders ---> [1, 2]
xs     ----^

xs.append(99)

orders ---> [1, 2, 99]
xs     ----^
```

### Mutable default argument pitfall

Default arguments are evaluated once when the function is defined.

```python
def add_symbol(symbol: str, seen: list[str] = []):  # bug
    seen.append(symbol)
    return seen

print(add_symbol("AAPL"))  # ['AAPL']
print(add_symbol("MSFT"))  # ['AAPL', 'MSFT'] unexpected shared state
```

Production-safe pattern:

```python
def add_symbol(symbol: str, seen: list[str] | None = None) -> list[str]:
    if seen is None:
        seen = []
    seen.append(symbol)
    return seen
```

Backend bug version:

```python
def build_headers(token: str, headers: dict[str, str] = {}):  # bug
    headers["Authorization"] = f"Bearer {token}"
    return headers

# In a worker, one request can accidentally inherit/overwrite another request's data.
```

### Tuples containing mutable objects

A tuple is immutable only at the top level.

```python
position = (["AAPL", "MSFT"], "strategy-a")
position[0].append("NVDA")

print(position)  # (['AAPL', 'MSFT', 'NVDA'], 'strategy-a')
# position[0] = []  # TypeError: top-level tuple assignment is blocked
```

Interview trap: saying "tuples are always safe immutable records." They are not if they contain mutable objects.

### Thread-safety implication

Immutables are safer to share between threads because no thread can mutate them. Mutable shared state needs locking or ownership discipline.

```python
import threading

limits = {"AAPL": 100}
lock = threading.Lock()

def update_limit(symbol: str, value: int) -> None:
    with lock:
        limits[symbol] = value
```

The GIL does not make compound business logic atomic. See [[Concurrency GIL async and multiprocessing]].

### Quick revision

- Assignment does not copy objects.
- Mutable objects can change through any alias.
- Immutable updates rebind names to new objects.
- Mutable defaults are shared across calls.
- Tuple immutability is shallow.
- In production, accidental mutation causes request leakage, config corruption, and flaky tests.

---

## Shallow copy vs deep copy

### Concept

| Operation | Outer object | Nested objects |
| --- | --- | --- |
| `b = a` | Same | Same |
| `copy.copy(a)`, `a.copy()`, `a[:]` | New | Shared |
| `copy.deepcopy(a)` | New | Recursively copied |

Why backend systems care:

- Config and request dictionaries are often nested.
- Shallow copying a template can still mutate the template's nested lists/dicts.
- Deep copying large object graphs can hurt latency and memory.

### Diagrams

Shallow copy:

```text
original ---> dict A ---> nested risk dict
copy     ---> dict B ----^
```

Deep copy:

```text
original ---> dict A ---> nested risk dict A
copy     ---> dict B ---> nested risk dict B
```

### Runnable example

```python
import copy

template = {
    "symbol": "AAPL",
    "risk": {"checks": ["max_qty", "price_band"]},
}

shallow = template.copy()
shallow["risk"]["checks"].append("symbol_allowed")

print(template["risk"]["checks"])
# ['max_qty', 'price_band', 'symbol_allowed']

deep = copy.deepcopy(template)
deep["risk"]["checks"].append("venue_allowed")

print(template["risk"]["checks"])
# unchanged by `deep`
```

### Edge cases

`deepcopy` preserves cycles and repeated references using a memo table.

```python
import copy

shared = ["risk"]
obj = [shared, shared]
clone = copy.deepcopy(obj)

print(clone[0] is clone[1])  # True: internal alias preserved
print(clone[0] is shared)    # False: detached from original
```

Not everything should be deep-copied: sockets, locks, files, DB sessions, thread pools, generators, and many C-extension objects need explicit lifecycle handling.

### Performance

```python
large = [{"id": i, "tags": []} for i in range(100_000)]

shallow = large.copy()  # copies references only
# deep = copy.deepcopy(large)  # copies every dict/list reachable from large
```

In HFT or low-latency services, repeated `deepcopy` in hot paths can create allocation spikes and tail-latency outliers. Prefer immutable templates, explicit constructors, or copy-on-write.

### Quick revision

- Shallow copy isolates one level only.
- Deep copy recursively copies reachable objects.
- Nested mutables are the common bug source.
- `deepcopy` is safer but often too expensive for hot paths.
- Explicit ownership beats blind copying.

---

## `is` vs `==`

### Concept

| Operator | Meaning | Use |
| --- | --- | --- |
| `is` | Object identity: same object in memory | `x is None`, sentinels, singleton checks |
| `==` | Value equality via `__eq__` | Most value comparisons |

Why backend systems care:

- Identity bugs can pass tests accidentally because CPython interns small ints and some strings.
- API values, DB values, and deserialized JSON objects should be compared by value, not identity.

### Runnable examples

```python
a = [1, 2]
b = [1, 2]

print(a == b)  # True: same value
print(a is b)  # False: different list objects
```

Interning trap:

```python
x = 256
y = 256
print(x == y)  # True
# x is y may be True in CPython due to small-int caching; do not rely on it.
```

Correct `None` check:

```python
def get_timeout(timeout: float | None) -> float:
    if timeout is None:
        return 1.0
    return timeout
```

Why `is None` is preferred: `None` is a singleton, and `== None` can invoke user-defined `__eq__`.

```python
class Weird:
    def __eq__(self, other):
        return True

value = Weird()
print(value == None)  # True, misleading
print(value is None)  # False
```

### Quick revision

- Use `==` for values.
- Use `is` for identity/singletons: `None`, `True`, `False`, custom sentinel objects.
- Interning is an implementation optimization, not program logic.
- Interview trap: `a is b` for small strings/ints may appear to work.

---

## List vs tuple

### Concept

| Feature | `list` | `tuple` |
| --- | --- | --- |
| Mutability | Mutable | Immutable at top level |
| Append/remove | Yes | No |
| Hashable | No | Only if all elements are hashable |
| Memory | More overhead, over-allocation for growth | Usually smaller |
| Use case | Working collection | Fixed record, key, snapshot |

Why backend systems care:

- Lists are good for accumulating data.
- Tuples are good for stable records, composite keys, and immutable snapshots.
- Hashable tuples can be used as dict keys for routing, caching, or exchange/symbol lookup.

### Runnable examples

```python
orders = []
orders.append(("AAPL", 100))
orders.append(("MSFT", 50))

route_cache = {
    ("NASDAQ", "AAPL"): "connector-1",
    ("NYSE", "IBM"): "connector-2",
}

print(route_cache[("NASDAQ", "AAPL")])
```

Hashing trap:

```python
good_key = ("AAPL", 100)
bad_key = ("AAPL", [100])

print(hash(good_key))
# hash(bad_key)  # TypeError: unhashable type: 'list'
```

### Performance

- `list.append` is amortized O(1).
- Tuple creation can be cheaper for fixed-size records.
- Lists over-allocate to support growth.
- Tuple immutability can improve safety and hashability, not magically speed up all code.

### Quick revision

- Use lists for changing collections.
- Use tuples for fixed records and dict/set keys.
- Tuple immutability is shallow.
- Do not choose tuple only for "performance" unless it matches the data model.

---

## Set vs dict

### Concept

Both sets and dicts are hash-table based.

| Structure | Stores | Typical use |
| --- | --- | --- |
| `set` | Unique hashable values | membership, deduplication |
| `dict` | key -> value mapping | lookup, caching, indexes |

Average lookup/insert/delete is O(1), but worst case can degrade with pathological collisions.

Why backend systems care:

- Sets are ideal for idempotency keys, seen order IDs, allowed symbols, enabled feature flags.
- Dicts are ideal for connection registries, routing tables, caches, correlation IDs, state by order ID.

### Runnable examples

```python
seen_order_ids: set[str] = set()

def should_process(order_id: str) -> bool:
    if order_id in seen_order_ids:
        return False
    seen_order_ids.add(order_id)
    return True

print(should_process("o-1"))  # True
print(should_process("o-1"))  # False
```

Dict backend lookup:

```python
connectors = {
    "NASDAQ": "nasdaq-client",
    "NYSE": "nyse-client",
}

venue = "NASDAQ"
client = connectors.get(venue)
if client is None:
    raise LookupError(f"missing connector for {venue}")
```

Hashing edge case:

```python
class BadKey:
    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return isinstance(other, BadKey) and self.value == other.value

key = BadKey("AAPL")
d = {key: "route"}
key.value = "MSFT"  # bug: object hash changed after insertion

print(d.get(key))  # often None: dict invariants broken
```

Production lesson: dict/set keys must be hash-stable.

### Quick revision

- Sets and dicts rely on hashing.
- Keys/elements must be hashable and stable.
- Use sets for uniqueness/membership.
- Use dicts for lookup and state indexing.
- Do not mutate objects used as dict keys or set members.
