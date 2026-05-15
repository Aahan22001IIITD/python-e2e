# Python Backend/HFT Systems Interview Notes

Tags: #python #backend #hft #systems #interview

Role focus: Python services, exchange connectors, APIs, automation, Linux workflows, monitoring, reliability, concurrency, performance tuning, and distributed backend systems.

Use this as a quick-revision map:

## 01 Python Core

- [[01 Python Core/Core object semantics]] — mutability, copy behavior, identity/equality, list vs tuple, set vs dict
- [[01 Python Core/Collections and counting patterns]] — `defaultdict`, `deque`, `Counter`, backend use cases

## 02 Runtime Patterns

- [[02 Runtime Patterns/Comprehensions functional tools and iteration]] — comprehensions, generator expressions, `lambda`, `map`, `filter`, iterators, generators
- [[02 Runtime Patterns/Decorators context managers and exceptions]] — production wrappers, resource safety, retries, logging
- [[02 Runtime Patterns/Functions classes and architecture]] — `*args`, `**kwargs`, class methods, static methods, inheritance, polymorphism, composition
- [[02 Runtime Patterns/Concurrency GIL async and multiprocessing]] — threading, multiprocessing, GIL, `async`/`await`, backend concurrency choices
- [[02 Runtime Patterns/File and JSON handling]] — streaming files, parsing APIs, safe serialization

## 03 Production Revision

- [[03 Production Revision/Interview question bank]]
- [[03 Production Revision/Interview question bank solutions]]
- [[03 Production Revision/One hour revision]]
- [[03 Production Revision/Coding exercises]]

## How to answer in interviews

For most Python backend questions, answer in this order:

1. Define the concept precisely.
2. Explain object ownership / references / lifecycle.
3. Give the backend failure mode.
4. Mention performance or concurrency tradeoff.
5. Show the safe production pattern.

Example:

```python
def answer_pattern():
    return [
        "what it is",
        "why it matters in memory/reference behavior",
        "production bug it prevents",
        "performance tradeoff",
        "safe code pattern",
    ]
```
