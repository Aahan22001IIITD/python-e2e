# Core object semantics

Tags: #python #mutability #copying #identity #hashing #backend #hft

This note explains the Python object behavior that commonly affects backend code: shared request data, config objects, caches, dict keys, and concurrent workers.

See also: [[Python mutability — interview note]], [[Python shallow copy vs deep copy]], [[Concurrency GIL async and multiprocessing]]

---

## Mutable vs immutable

Python variables are names pointing to objects. Assignment does not copy the object. Mutability is about whether the object itself can change in place.

| Category | Examples | What happens on change |
| --- | --- | --- |
| Immutable | `int`, `float`, `bool`, `str`, `bytes`, `tuple` of immutable values, `frozenset`, `None` | Python creates a new object or rebinds the name |
| Mutable | `list`, `dict`, `set`, `bytearray`, most class instances | The same object can be changed in place |

Backend reason: long-running services often pass the same request, config, or cache object through many functions. If one function mutates shared state, another function may see the changed value.

```python
def mutate_list(xs: list[int]) -> None:
    xs.append(99)


def rebind_int(n: int) -> None:
    n += 1


orders = [1, 2]
mutate_list(orders)
print(orders)

count = 10
rebind_int(count)
print(count)
```

Output:

```text
[1, 2, 99]
10
```

Why: `orders` and `xs` point to the same list, so `append` changes the caller's list. `n += 1` creates/rebinds a local integer name, so the caller's `count` is unchanged.

Keep in mind: shared mutable objects need clear ownership. If a function should not mutate input, return a new object or document the mutation clearly.

---

## Mutable default arguments

Default argument values are created once when the function is defined, not once per call. This matters when the default is mutable.

```python
def add_symbol(symbol: str, seen: list[str] = []):
    seen.append(symbol)
    return seen


print(add_symbol("AAPL"))
print(add_symbol("MSFT"))
```

Output:

```text
['AAPL']
['AAPL', 'MSFT']
```

Why: both calls reuse the same default list. In a backend service, the same mistake can leak request state between users or tests.

Use `None` and create a fresh list inside the function:

```python
def add_symbol(symbol: str, seen: list[str] | None = None) -> list[str]:
    if seen is None:
        seen = []
    seen.append(symbol)
    return seen
```

---

## Tuples containing mutable objects

A tuple is immutable only at the top level. You cannot replace a tuple slot, but you can still mutate a mutable object stored inside it.

```python
position = (["AAPL", "MSFT"], "strategy-a")
position[0].append("NVDA")

print(position)
```

Output:

```text
(['AAPL', 'MSFT', 'NVDA'], 'strategy-a')
```

Why: the tuple still points to the same list, and the list itself is mutable.

Keep in mind: use tuples of immutable values when you need stable records, snapshots, or dict keys.

---

## Shallow copy vs deep copy

Copying has levels. The important question is whether nested objects are copied or shared.

| Operation | Outer object | Nested objects |
| --- | --- | --- |
| `b = a` | Same object | Same objects |
| `copy.copy(a)`, `a.copy()`, `a[:]` | New object | Shared objects |
| `copy.deepcopy(a)` | New object | Recursively copied objects |

```python
import copy

template = {
    "symbol": "AAPL",
    "risk": {"checks": ["max_qty", "price_band"]},
}

shallow = template.copy()
shallow["risk"]["checks"].append("symbol_allowed")
print(template["risk"]["checks"])

deep = copy.deepcopy(template)
deep["risk"]["checks"].append("venue_allowed")
print(template["risk"]["checks"])
```

Output:

```text
['max_qty', 'price_band', 'symbol_allowed']
['max_qty', 'price_band', 'symbol_allowed']
```

Why: the shallow copy gets a new outer dict but shares the nested `risk` dict and `checks` list. The deep copy gets its own nested objects.

Keep in mind: `deepcopy` is useful at boundaries, but repeated deep copies in hot paths can hurt latency and memory. Prefer explicit constructors, immutable templates, or copying only the fields you will mutate.

---

## `is` vs `==`

Use `==` to compare values. Use `is` to check identity, especially for `None` and sentinel objects.

```python
a = [1, 2]
b = [1, 2]

print(a == b)
print(a is b)
```

Output:

```text
True
False
```

Why: the two lists contain equal values, but they are different list objects.

```python
class Weird:
    def __eq__(self, other):
        return True


value = Weird()
print(value == None)
print(value is None)
```

Output:

```text
True
False
```

Why: `== None` can call user-defined equality logic. `is None` checks whether the object is actually the `None` singleton.

Keep in mind: CPython may reuse some small integers and strings internally. Do not build logic on `x is y` for normal values.

---

## List vs tuple

Use a list for a collection that changes. Use a tuple for a fixed record, snapshot, or hashable key.

| Feature | `list` | `tuple` |
| --- | --- | --- |
| Mutability | Mutable | Immutable at top level |
| Append/remove | Yes | No |
| Hashable | No | Yes, only if every element is hashable |
| Common use | Building or changing data | Fixed record, key, snapshot |

```python
orders = []
orders.append(("AAPL", 100))
orders.append(("MSFT", 50))

route_cache = {
    ("NASDAQ", "AAPL"): "connector-1",
    ("NYSE", "IBM"): "connector-2",
}

print(orders)
print(route_cache[("NASDAQ", "AAPL")])
```

Output:

```text
[('AAPL', 100), ('MSFT', 50)]
connector-1
```

Why: the list is good for accumulating orders. The tuple is good as a dict key because it is fixed and hashable.

Keep in mind: a tuple containing a list is not hashable, because the nested list can change.

---

## Set vs dict

Both sets and dicts are hash-table based. Sets store unique values. Dicts map keys to values.

| Structure | Stores | Typical backend use |
| --- | --- | --- |
| `set` | Unique hashable values | membership, deduplication, idempotency keys |
| `dict` | key -> value mapping | routing tables, caches, indexes, state by ID |

```python
seen_order_ids: set[str] = set()


def should_process(order_id: str) -> bool:
    if order_id in seen_order_ids:
        return False
    seen_order_ids.add(order_id)
    return True


print(should_process("o-1"))
print(should_process("o-1"))
```

Output:

```text
True
False
```

Why: the set gives fast membership checks and stores each order ID only once.

```python
connectors = {
    "NASDAQ": "nasdaq-client",
    "NYSE": "nyse-client",
}

venue = "NASDAQ"
print(connectors.get(venue))
```

Output:

```text
nasdaq-client
```

Why: the dict maps a venue name to the client used for that venue.

Keep in mind: dict keys and set elements must stay hash-stable. Do not mutate an object after using it as a key or set member.

---

## Quick revision

- Assignment does not copy objects.
- Mutable objects can change through any alias.
- Mutable defaults are shared across calls, so use `None` plus a fresh object.
- Shallow copy copies one level; deep copy copies nested objects too.
- Use `==` for values and `is` for `None`/singletons.
- Use lists for changing collections and tuples for fixed records or keys.
- Use sets for membership and dicts for lookup.
