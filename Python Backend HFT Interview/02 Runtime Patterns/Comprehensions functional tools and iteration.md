# Comprehensions, functional tools, and iteration

Tags: #python #iteration #generators #comprehensions #backend #hft

This note covers data-transformation patterns used in API handlers, log processors, ETL jobs, exchange connector code, and interview coding screens.

---

## Comprehensions

### Concept

Comprehensions build lists, sets, and dicts using compact iteration syntax.

| Type | Example | Result |
| --- | --- | --- |
| List | `[x * 2 for x in xs]` | list |
| Set | `{x for x in xs}` | unique values |
| Dict | `{k: v for k, v in pairs}` | mapping |
| Generator expression | `(x for x in xs)` | lazy iterator |

Why backend systems care:

- Useful for transforming request payloads, DB rows, logs, and API responses.
- Easy to read when simple; harmful when nested/clever.
- Generator expressions avoid materializing large intermediate lists.

### Runnable examples

```python
orders = [
    {"id": "1", "symbol": "AAPL", "qty": 100, "status": "open"},
    {"id": "2", "symbol": "MSFT", "qty": 0, "status": "rejected"},
    {"id": "3", "symbol": "AAPL", "qty": 50, "status": "open"},
]

open_ids = [o["id"] for o in orders if o["status"] == "open"]
symbols = {o["symbol"] for o in orders}
qty_by_id = {o["id"]: o["qty"] for o in orders}

print(open_ids)
print(symbols)
print(qty_by_id)
```

Generator expression for memory efficiency:

```python
total_qty = sum(o["qty"] for o in orders if o["status"] == "open")
print(total_qty)
```

Readable vs overused:

```python
# Good
active_symbols = {o["symbol"] for o in orders if o["qty"] > 0}

# Too dense for production code; split it.
bad = {o["symbol"]: o["qty"] for o in orders if o["qty"] > 0 and o["status"] == "open"}
```

### Edge cases

Late binding trap with lambdas inside comprehensions/loops:

```python
funcs = [lambda: i for i in range(3)]
print([f() for f in funcs])  # [2, 2, 2]

fixed = [lambda i=i: i for i in range(3)]
print([f() for f in fixed])  # [0, 1, 2]
```

### Quick revision

- Use comprehensions for simple transformations.
- Use generator expressions for streaming into `sum`, `any`, `all`, `Counter`, etc.
- Avoid nested unreadable comprehensions in production.
- Watch closure late-binding traps.

---

## `lambda`, `map`, and `filter`

### Concept

`lambda` creates small anonymous functions. `map` applies a function. `filter` keeps items where a predicate is truthy.

Why backend systems care:

- Useful for small transformations in pipelines.
- Often less readable than comprehensions in Python.
- Interviewers may test whether you know both styles and choose idiomatic code.

### Runnable examples

```python
orders = [
    {"symbol": "AAPL", "qty": 100},
    {"symbol": "MSFT", "qty": 0},
]

symbols = list(map(lambda o: o["symbol"], orders))
nonzero = list(filter(lambda o: o["qty"] > 0, orders))

print(symbols)
print(nonzero)
```

More idiomatic Python:

```python
symbols = [o["symbol"] for o in orders]
nonzero = [o for o in orders if o["qty"] > 0]
```

Backend use case with a named function:

```python
def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()

raw_symbols = [" aapl ", "msft", " NvDa "]
normalized = list(map(normalize_symbol, raw_symbols))
print(normalized)
```

### Performance considerations

- `map`/`filter` are lazy in Python 3; convert to `list` only when needed.
- Comprehensions are often clearer and commonly faster for simple Python-level operations.
- Named functions improve stack traces and logging.

### Interview traps

- Forgetting `map` returns an iterator in Python 3.
- Using `lambda` for complex business logic.
- Losing debuggability with anonymous callbacks.

### Quick revision

- Prefer comprehensions for simple transformations.
- Use named functions for non-trivial logic.
- Remember `map`/`filter` are lazy.
- Avoid lambda-heavy production code when readability matters.

---

## Iterators

### Concept

An iterable can produce an iterator. An iterator returns values one at a time using `next()` and raises `StopIteration` when exhausted.

```python
xs = [10, 20]
it = iter(xs)

print(next(it))  # 10
print(next(it))  # 20
# next(it)       # StopIteration
```

Why backend systems care:

- Streaming files, DB cursors, network messages, and paginated APIs are iterator-shaped.
- Iterators avoid loading all data into memory.
- Exhausted iterators are a common bug.

### Custom iterator

```python
class RetrySchedule:
    def __init__(self, delays: list[float]):
        self._delays = delays
        self._index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self._delays):
            raise StopIteration
        value = self._delays[self._index]
        self._index += 1
        return value

for delay in RetrySchedule([0.1, 0.2, 0.5]):
    print(delay)
```

Often simpler as a generator:

```python
def retry_schedule():
    yield 0.1
    yield 0.2
    yield 0.5
```

### Edge case: iterator exhaustion

```python
rows = iter([1, 2, 3])
print(list(rows))  # [1, 2, 3]
print(list(rows))  # [] already consumed
```

### Quick revision

- Iterable: can be passed to `iter()`.
- Iterator: has `__next__()` and is consumed.
- `StopIteration` ends iteration.
- Streaming APIs are often iterator/generator based.

---

## Generators and `yield`

### Concept

A generator is a lazy iterator created by a function using `yield`.

Why backend systems care:

- Process large files/logs without loading everything.
- Stream API responses.
- Implement pipelines for market data/events.
- Reduce memory pressure in long-running services.

### Runnable examples

```python
def parse_lines(lines: list[str]):
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        yield line.upper()

for item in parse_lines(["aapl", "", "#comment", "msft"]):
    print(item)
```

Streaming large file style:

```python
def read_symbols(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            symbol = line.strip()
            if symbol:
                yield symbol
```

Pipeline:

```python
def valid_orders(rows):
    for row in rows:
        if row["qty"] > 0:
            yield row

def symbols(rows):
    for row in rows:
        yield row["symbol"]

orders = [{"symbol": "AAPL", "qty": 10}, {"symbol": "MSFT", "qty": 0}]
print(list(symbols(valid_orders(orders))))  # ['AAPL']
```

### Async relation

Regular generator:

```python
def events():
    yield "tick"
```

Async generator:

```python
import asyncio

async def async_events():
    await asyncio.sleep(0.01)
    yield "tick"
```

Async generators are useful for WebSockets, streaming responses, and async message sources.

### Performance

- Generators reduce peak memory.
- They add a small per-item overhead; for tiny data, lists may be simpler.
- They are one-pass; materialize with `list()` only when needed.

### Quick revision

- `yield` pauses and resumes function state.
- Generators are lazy and memory-efficient.
- Great for large logs, files, streaming data.
- Beware one-time consumption and hidden side effects during iteration.
