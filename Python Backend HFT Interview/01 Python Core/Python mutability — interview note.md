# Python: mutable vs immutable (backend / HFT interviews)

Tags: #python #memory-model #concurrency #interview

---

## Definitions

| Concept | Meaning |
| --- | --- |
| **Immutable** | Object’s *value* (the data it represents) cannot be changed in place. Operations that “modify” it return a **new** object. |
| **Mutable** | Object’s internal state can be changed **in place**; other references see the same object update. |
| **Identity** | `id(x)` / `x is y` — *which* object in memory. |
| **Equality** | `x == y` — same *value* (per `__eq__`). |

**Immutable built-ins (common):** `int`, `float`, `complex`, `bool`, `str`, `bytes`, `tuple` (of immutable elements), `frozenset`, `None`, many `datetime` values (treat as immutable *in use*; some types have internal optimization detail).

**Mutable built-ins:** `list`, `dict`, `set`, `bytearray`, most user-defined instances unless you freeze them (`dataclass(frozen=True)` only affects attribute assignment—not deep immutability of nested mutables).

**Interview line:** Immutability is a property of **object type + how you use it**, not Python variables. Variables are **names bound to objects**.

---

## Memory behavior

- Assignment **rebinds the name**, it does not copy objects: `a = b` makes both names refer to the **same object** unless you explicitly copy.
- Small integers and some strings may be **interned/cached** (CPython detail). Do **not** rely on `is` for equality of values; rely on `==`.
- Mutable objects allocate **fixed header + grows** (lists over-allocate); appending often amortized O(1), but **capacity** grows. Immutable “updates” (e.g. string concat in a loop) create **many** short-lived objects → GC pressure.
- **Copy semantics:** `copy.copy` is shallow; nested mutables are still shared. `copy.deepcopy` is recursive and expensive.

```python
a = [1, 2]
b = a
b.append(3)   # a is [1, 2, 3] — same list object

s = "hi"
t = s
# s += "!"  # binds s to a NEW str; t still "hi"
```

---

## Examples (identity vs mutation)

```python
x = [1, 2, 3]
y = x
y[0] = 99
assert x[0] == 99  # same list

u = (1, 2, 3)
# u[0] = 0  # TypeError: tuple is immutable

def bump(n: int) -> None:
    n = n + 1   # rebinds local n; caller unchanged

def bump_list(xs: list) -> None:
    xs.append(1)  # mutates caller's object if same reference
```

---

## Mutable default argument pitfalls

**The trap:** Default arguments are evaluated **once** at **function definition** time, not each call.

```python
def append_one(item, bag=[]):  # DON'T
    bag.append(item)
    return bag

a = append_one(1)  # [1]
b = append_one(2)  # [1, 2] — surprise: shared `bag`
```

**Fixes:**

```python
def append_one(item, bag=None):
    if bag is None:
        bag = []
    bag.append(item)
    return bag
```

**Interview angle:** Explains weird “stateful” functions, flaky tests, and cross-request leakage if someone misuses this in a long-lived process.

---

## Strings vs lists

| | `str` | `list` |
| --- | --- | --- |
| Character / element update | No — new `str` | Yes — in place |
| Concat many times | Often O(n²) if done naïvely | Amortized O(n) with `append` |
| Hashable | Yes (if str) | No |
| Use as dict key | Yes | No (unhashable) |

```python
# Bad in hot paths: repeated str concat
s = ""
for chunk in parts:
    s += chunk   # new string each iteration

# Better: list + join
s = "".join(parts)
```

**Bytes note:** `bytes` is immutable; `bytearray` is mutable—relevant for parsers, sockets, zero-copy style code.

---

## Tuples containing mutable objects

The **tuple** is immutable: you cannot reassign **which** object sits at index `i`, but if that object is mutable, **its contents** can change.

```python
t = ([1], 2)
t[0].append(2)   # OK: mutating the list inside
# t[0] = []      # TypeError: tuple assignment

# tuple hash only if all elements are hashable
d = {}
# d[t] = 1       # TypeError if t contains unhashable nested list
```

**Interview trap:** Saying “tuples are read-only copies of data” — false for nested structures. Use `typing.Tuple` docs + shallow vs deep semantics.

---

## Interview traps

1. **`is` vs `==`:** `is` is identity; equality is value. Cached small ints `(a is b)` sometimes “works”; never part of portable logic.
2. **Thinking assignment copies:** It does not; use `list(x)`, `x[:]`, `copy.copy`, or comprehension as needed.
3. **Frozen dataclass myths:** Attributes can’t be reassigned, but a `list` field can still `.append()` unless you enforce immutability (e.g. tuples, Mapping, third-party immutable collections).
4. **Default args** and **late binding in closures/lambdas in loops** (`lambda: i` capturing one `i`) — sibling foot-guns often asked together.

```python
funcs = [lambda: i for i in range(3)]
[f() for f in funcs]  # often [2, 2, 2] — one shared i
```

5. **`+=` on lists:** `x += [1]` calls `__iadd__` — **mutates** in place. `x = x + [1]` binds new list. Subtle differences with other references watching `x`.

---

## Performance implications

- **Allocations:** Immutable “changes” multiply objects → **allocation rate**, cache misses, GC pauses matter in **HFT / low-latency** paths (still often secondary to I/O and algorithm, but real in hot loops).
- **Sharing:** Immutables are safe to share without defensive copies; mutables often need **copy-on-write** discipline or immutable data structures (`tuple`, `frozenset`, persistent structures in some libs).
- **Dict/set keys:** Require **hashable** (immutable-ish) keys; mutating an object while it conceptually participates in hashing breaks invariants (**never mutate `__hash__`-ed mutable content**).

```python
# Anti-pattern
d = {}
k = []
d[id(k)] = "..."  # not using list as key, but illustrating: mutating keys is invalid
```

- **Structural sharing:** Understand **shallow copy cost** vs **deep copy** for large graphs (risk in serialization, config merges).

---

## Threading / concurrency

CPython **`threading`** + **GIL:** One thread executes Python bytecode at a time; GIL reduces **race on single bytecode ops** but **does not** make multi-step updates atomic.

```python
# Not atomic across threads despite GIL illusion in simple tests
balance += amount   # READ-modify-WRITE race with another thread
if key in d:
    d[key].append(x)  # still racy: another thread may delete key
```

**Implications:**

- **Mutable shared state** between threads needs **locks** (`threading.Lock`), **queues**, or **immutable message passing** (copy data or use immutable snapshots).
- **`multiprocessing`:** Separate memory — mutating in child doesn’t touch parent unless using shared proxies; deserialization often creates **fresh** mutable copies (watch **stale caches** across processes).

**Interview answer structure:** Identify **shared mutable** → define **critical sections** → prefer **immutable snapshots** / **structures with clear ownership** → if async, cooperative multitasking doesn’t preempt mid-bytecode identically everywhere but logical races on shared dicts/lists still occur.

---

## Common bugs in production systems

| Pattern | Failure mode |
| --- | --- |
| Shared mutable **default** args / caches on module-level globals | Cross-request bleed in HTTP workers, flaky tests |
| Passing **nested dict/list** configs without deep copy | One service mutates “constants” affecting others |
| **Shallow copy** before passing to callbacks |Callee mutates nested list — caller corrupted |
| “Return internal list” anti-pattern (`return self._items`) | Caller mutates protected state |
| Concurrency **check-then-act** on dict/list/set | TOCTOU races under threads |
| C extension / `numpy` semantics | Bypass Python-level expectations; mutate buffers out of sight |
| **Logging / repr** holding references to huge mutable structures | Keeps graphs alive unintentionally |

**Defensive patterns:** Return `tuple(self._items)`, `MappingProxyType`, copy at boundaries, document ownership (“caller must not mutate”), use locks or process isolation.

---

## Quick revision summary

- **Immutable:** cannot change value in place; rebinding or new object. **Mutable:** in-place change; **aliases see updates**.
- **Assignment shares references;** use explicit copies when isolation is required.
- **Mutable defaults** bind once — use `None` + fresh object per call.
- **Tuple immutability** is **shallow**; nested lists still mutate.
- **`str` concat in loops** can be costly; **`list` + `join`** for building text.
- **Performance:** allocation churn on immutables; hashable keys need stable contents.
- **Threads:** GIL ≠ thread safety for multi-step logic; **lock** or **don’t share mutables**.
- **Production bugs:** shared caches, shallow copies, exposing internal collections, TOCTOU races.

---

## See also

- [[Interview]] — link this note from your workbook’s technical section.
- [[Welcome]] — vault index
