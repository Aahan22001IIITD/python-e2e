# Concurrency, GIL, async, and multiprocessing

Tags: #python #concurrency #gil #asyncio #threading #multiprocessing #backend #hft

Concurrency questions matter for Python backend/HFT roles because trading systems spend time on network IO, market data, order routing, queues, serialization, and monitoring. The right answer is usually about choosing the correct concurrency model for the workload.

---

## Concurrency vs parallelism

| Concept     | Meaning                               | Python tool                        |
| ----------- | ------------------------------------- | ---------------------------------- |
| Concurrency | Manage many tasks in overlapping time | `asyncio`, threads                 |
| Parallelism | Execute CPU work at the same time     | multiprocessing, native extensions |

Backend relevance:

- IO-bound: HTTP calls, DB queries, sockets, exchange APIs.
- CPU-bound: pricing, risk calculations, compression, parsing hot loops.
- HFT concern: avoid latency spikes from locks, context switches, allocations, and blocking calls on event loops.

---

## Threading vs multiprocessing

### Concept

| Workload                | Good fit                        | Why                                   |
| ----------------------- | ------------------------------- | ------------------------------------- |
| IO-bound                | Threads or async                | Waiting releases time for other tasks |
| CPU-bound Python code   | Multiprocessing                 | Avoids GIL limitation                 |
| Low-latency socket loop | Often async or dedicated thread | Clear ownership, less lock contention |

### Threading example: IO-style concurrency

```python
import threading
import time

def fetch_quote(symbol: str) -> None:
    time.sleep(0.1)  # pretend network call
    print("quote", symbol)

threads = [threading.Thread(target=fetch_quote, args=(s,)) for s in ["AAPL", "MSFT"]]

for t in threads:
    t.start()
for t in threads:
    t.join()
```

### Multiprocessing example: CPU work

```python
from multiprocessing import Pool

def score(x: int) -> int:
    return sum(i * i for i in range(x))

if __name__ == "__main__":
    with Pool() as pool:
        print(pool.map(score, [10_000, 20_000, 30_000]))
```

Memory implication:

- Threads share process memory: cheap communication, but shared-state races.
- Processes have separate memory: safer isolation, but serialization/pickling overhead.

### Common threading bug

```python
import threading

counter = 0

def inc():
    global counter
    for _ in range(100_000):
        counter += 1  # read-modify-write is not business-logic safe

threads = [threading.Thread(target=inc) for _ in range(2)]
for t in threads: t.start()
for t in threads: t.join()

print(counter)  # can be less than expected depending on runtime/interleavings
```

Safe version:

```python
import threading

counter = 0
lock = threading.Lock()

def inc_safe():
    global counter
    for _ in range(100_000):
        with lock:
            counter += 1
```

### Quick revision

- Threads share memory; processes do not.
- Threads help IO-bound work.
- Processes help CPU-bound Python work.
- Shared mutable state needs locks, queues, or ownership discipline.

---

## GIL

### Concept

The Global Interpreter Lock allows only one thread to execute Python bytecode at a time in CPython.

Why it exists:

- Simplifies CPython memory management and reference counting.
- Many C extensions and internals historically assume this model.

Impact:

- Threads do not usually speed up CPU-bound pure Python code.
- Threads can still help IO-bound workloads because blocking IO releases the GIL.
- C extensions may release the GIL for heavy native work.

### Interview misconception example

```python
import threading

def cpu_bound():
    total = 0
    for i in range(5_000_000):
        total += i * i
    return total

# Running this in multiple threads generally will not give linear speedup in CPython.
```

### Backend relevance

- Web services often benefit from threads because they wait on network/DB IO.
- CPU-heavy handlers should move work to processes, native code, worker queues, or separate services.
- Do not blame the GIL for all latency; serialization, locks, network hops, GC, and DB calls often dominate.

### Quick revision

- GIL limits parallel Python bytecode execution.
- IO-bound threads can still be useful.
- CPU-bound Python usually needs multiprocessing/native code.
- The GIL does not make your data structures logically thread-safe.

---

## `async` / `await` basics

### Concept

`asyncio` runs many coroutines on an event loop. Coroutines voluntarily yield control at `await`.

Why backend systems care:

- Excellent for high-concurrency IO: HTTP clients, WebSockets, streaming, DB drivers, exchange connectors.
- Avoids one-thread-per-connection overhead.
- Blocking calls inside async code can stall the entire event loop.

### Runnable example

```python
import asyncio

async def fetch_quote(symbol: str) -> str:
    await asyncio.sleep(0.1)  # pretend async network call
    return f"{symbol}=100.00"

async def main():
    quotes = await asyncio.gather(
        fetch_quote("AAPL"),
        fetch_quote("MSFT"),
        fetch_quote("NVDA"),
    )
    print(quotes)

asyncio.run(main())
```

### FastAPI-style relevance

```python
# @app.get("/quote/{symbol}")
# async def quote(symbol: str):
#     result = await exchange_client.get_quote(symbol)
#     return {"symbol": symbol, "quote": result}
```

Async helps only if the called libraries are async/non-blocking.

### WebSocket / streaming style

```python
import asyncio

async def market_data_stream():
    for price in [100.1, 100.2, 99.9]:
        await asyncio.sleep(0.01)
        yield {"symbol": "AAPL", "price": price}

async def consume():
    async for event in market_data_stream():
        print(event)

asyncio.run(consume())
```

### Common async mistakes

```python
import asyncio
import time

async def bad_handler():
    time.sleep(1)  # bug: blocks event loop

async def good_handler():
    await asyncio.sleep(1)
```

CPU work inside async handler:

```python
async def bad_cpu_handler():
    # This blocks the event loop while it runs.
    return sum(i * i for i in range(10_000_000))
```

Use process pools/work queues for serious CPU work.

### Performance considerations

- Async improves throughput for IO-bound workloads, not CPU speed.
- Too many tasks can overwhelm downstream dependencies; use semaphores/backpressure.
- Always set timeouts on network calls.

```python
import asyncio

sem = asyncio.Semaphore(10)

async def guarded_call(symbol: str):
    async with sem:
        return await asyncio.wait_for(fetch_quote(symbol), timeout=0.5)
```

### Quick revision

- `async def` creates a coroutine function.
- `await` yields control while waiting.
- Async is best for high-concurrency IO.
- Never block the event loop with `time.sleep`, sync DB calls, or CPU-heavy loops.
- Use timeouts, cancellation handling, and backpressure.

---

## Backend concurrency decision table

| Scenario                        | Prefer                           | Reason                          |
| ------------------------------- | -------------------------------- | ------------------------------- |
| Many HTTP/exchange requests     | `asyncio` or threads             | IO-bound                        |
| CPU-heavy risk calculation      | multiprocessing/native extension | Avoid GIL                       |
| Simple background metrics flush | thread                           | Low complexity                  |
| WebSocket fan-in/fan-out        | async                            | Many concurrent sockets         |
| Shared in-memory cache updates  | locks or single owner task       | Avoid races                     |
| Ultra-low-latency hot path      | avoid unnecessary concurrency    | Predictability beats cleverness |

### Interview traps/questions

- Does the GIL prevent all race conditions?
  Answer: No. The GIL does not prevent logical race conditions. Operations that look simple can still interleave across multiple steps, and shared mutable state still needs locks, queues, or single-owner design.
- Why can threads help IO but not CPU-bound Python?
  Answer: Threads help IO-bound work because blocking network, disk, and DB calls can release the GIL while another thread runs. CPU-bound Python bytecode still competes for the GIL, so multiple threads usually do not give parallel speedup.
- What happens if you call blocking code in an async handler?
  Answer: Blocking code in an async handler stalls the event loop, delaying every other coroutine on that loop. Use async libraries, `await asyncio.sleep(...)`, executor offload, process pools, or a worker queue depending on the work.
- When would multiprocessing hurt performance?
  Answer: Multiprocessing can hurt when tasks are small, data is large to pickle, processes start frequently, memory duplication is high, or IPC costs dominate the actual computation.
- How do you prevent async overload?
  Answer: Prevent async overload with explicit limits: timeouts, semaphores, bounded queues, backpressure, cancellation handling, and downstream-aware rate limits.
