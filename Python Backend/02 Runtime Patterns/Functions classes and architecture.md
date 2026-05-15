# Functions, classes, and architecture

Tags: #python #oop #api-design #architecture #backend

These topics show whether you can design maintainable Python services, not just solve syntax questions.

---

## `*args` and `**kwargs`

### Concept

`*args` captures extra positional arguments. `**kwargs` captures extra keyword arguments. Unpacking sends iterable/mapping values into a function call.

Why backend systems care:

- Useful for decorators, adapters, logging wrappers, and client libraries.
- Dangerous when overused because signatures become unclear.
- Explicit function signatures help type checking, docs, and API stability.

### Runnable examples

```python
def log_event(event: str, *tags: str, **fields) -> None:
    print("event:", event)
    print("tags:", tags)
    print("fields:", fields)

log_event("order.accepted", "trading", venue="NASDAQ", symbol="AAPL")
```

Unpacking:

```python
def submit_order(symbol: str, qty: int, venue: str) -> dict:
    return {"symbol": symbol, "qty": qty, "venue": venue}

args = ("AAPL", 100)
kwargs = {"venue": "NASDAQ"}

print(submit_order(*args, **kwargs))
```

Decorator wrapper:

```python
from functools import wraps

def traced(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        print("call", fn.__name__)
        return fn(*args, **kwargs)
    return wrapper
```

### Common mistakes

```python
def bad_api(**kwargs):
    # Hard to know required fields, hard to type-check, easy to misspell.
    return kwargs["symbol"]
```

Prefer explicit parameters at public boundaries:

```python
def good_api(symbol: str, qty: int, venue: str) -> dict:
    return {"symbol": symbol, "qty": qty, "venue": venue}
```

### Quick revision

- `*args` = extra positional args.
- `**kwargs` = extra keyword args.
- Useful for wrappers and flexible internals.
- Avoid vague public APIs.

---

## `classmethod` vs `staticmethod`

### Concept

| Method type | First argument | Use case |
| --- | --- | --- |
| Instance method | `self` | uses object state |
| `@classmethod` | `cls` | alternative constructors, class-level polymorphism |
| `@staticmethod` | none implicit | namespaced utility related to class |

Why backend systems care:

- Factory methods create clients/configs cleanly.
- Class methods preserve subclass behavior.
- Static methods are often just module functions unless namespacing helps.

### Runnable examples

```python
class ExchangeConfig:
    def __init__(self, venue: str, endpoint: str):
        self.venue = venue
        self.endpoint = endpoint

    @classmethod
    def from_env(cls, env: dict[str, str]):
        return cls(venue=env["VENUE"], endpoint=env["ENDPOINT"])

    @staticmethod
    def normalize_venue(venue: str) -> str:
        return venue.strip().upper()

cfg = ExchangeConfig.from_env({"VENUE": " nasdaq ", "ENDPOINT": "tcp://feed"})
print(cfg.venue, cfg.endpoint)
print(ExchangeConfig.normalize_venue(" nyse "))
```

Subclass-friendly factory:

```python
class BaseClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    @classmethod
    def from_config(cls, config: dict):
        return cls(config["endpoint"])

class TestClient(BaseClient):
    pass

client = TestClient.from_config({"endpoint": "mock://exchange"})
print(type(client).__name__)  # TestClient
```

### Interview traps

- `staticmethod` does not receive class or instance.
- `classmethod` is better for alternative constructors.
- Do not use classes only to group static methods if a module function is clearer.

### Quick revision

- Use instance methods for object state.
- Use class methods for factories.
- Use static methods sparingly for related pure helpers.

---

## Inheritance and polymorphism

### Concept

Inheritance shares behavior through an `is-a` relationship. Polymorphism lets different implementations satisfy the same interface.

Why backend systems care:

- Exchange connectors, storage backends, and notification providers often share interfaces.
- Overuse of inheritance creates brittle hierarchies.
- Composition is often better for production systems because behavior changes independently.

### Runnable polymorphism example

```python
from abc import ABC, abstractmethod

class ExchangeConnector(ABC):
    @abstractmethod
    def send_order(self, symbol: str, qty: int) -> str:
        raise NotImplementedError

class NasdaqConnector(ExchangeConnector):
    def send_order(self, symbol: str, qty: int) -> str:
        return f"NASDAQ accepted {symbol} x {qty}"

class MockConnector(ExchangeConnector):
    def send_order(self, symbol: str, qty: int) -> str:
        return f"MOCK accepted {symbol} x {qty}"

def submit(connector: ExchangeConnector) -> str:
    return connector.send_order("AAPL", 100)

print(submit(NasdaqConnector()))
print(submit(MockConnector()))
```

Composition example:

```python
class RiskChecker:
    def validate(self, symbol: str, qty: int) -> None:
        if qty <= 0:
            raise ValueError("qty must be positive")

class OrderService:
    def __init__(self, connector: ExchangeConnector, risk: RiskChecker):
        self.connector = connector
        self.risk = risk

    def submit(self, symbol: str, qty: int) -> str:
        self.risk.validate(symbol, qty)
        return self.connector.send_order(symbol, qty)
```

### Composition vs inheritance

| Prefer | When |
| --- | --- |
| Inheritance | Stable `is-a` relationship, common interface, simple override points |
| Composition | Combining behaviors, replacing dependencies, testing, avoiding hierarchy explosion |

### Common mistakes

- Deep inheritance trees for simple configuration differences.
- Overriding methods without respecting base-class invariants.
- Using inheritance for code reuse when composition or a helper function is clearer.
- Forgetting that Python uses dynamic dispatch: method call resolved by runtime type.

### Quick revision

- Polymorphism is "same interface, different implementation."
- Use ABCs or protocols for connector-like boundaries.
- Prefer composition for backend services with swappable dependencies.
- Avoid inheritance when the relationship is not truly `is-a`.
