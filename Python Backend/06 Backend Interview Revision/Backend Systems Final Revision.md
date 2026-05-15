# Backend Systems Final Revision

Tags: #backend #systems #hft #interview #revision #production

Use this note in the final day or final hour before an interview. The goal is not to sound fancy. The goal is to explain what the system does, what can go wrong, and how you would make it reliable in production.

---

## How To Answer Backend Questions

A strong backend answer usually follows this order:

1. Define the API or contract.
2. Identify the state that must be stored.
3. Explain the normal flow.
4. Explain what can fail.
5. Add the safety pieces: timeout, retry, idempotency, transaction, logging, metrics, and rollback.
6. Explain how you would debug it in production.

Warning: do not jump directly to tools like Redis, Kafka, Kubernetes, or indexes. First explain the problem clearly, then choose the tool that solves that problem.

---

## Core Backend Concepts

### Authentication And Authorization

Authentication answers: "Who is the caller?" Examples are login, API keys, JWTs, sessions, and service credentials.

Authorization answers: "What is this caller allowed to do?" Example: a user may be logged in but still not allowed to cancel another user's order.

Good interview answer:

```text
Authentication proves identity. Authorization checks permissions after identity is known.
For an order API, I would authenticate the user or service first, then check whether that account can create, view, or cancel the specific order.
```

Warning: `401` usually means the caller is not authenticated. `403` means the caller is authenticated but not allowed.

### HTTP Status Codes

Use status codes to tell the client what kind of problem happened.

- `400`: request is malformed or invalid.
- `401`: missing or invalid authentication.
- `403`: authenticated caller is not allowed.
- `404`: resource does not exist or should not be revealed.
- `409`: request conflicts with current state, such as duplicate idempotency key with different payload.
- `429`: caller is sending too many requests.
- `500`: unexpected server bug.
- `503`: service or dependency is temporarily unavailable.
- `504`: upstream dependency timed out.

Good interview answer:

```text
I would separate client errors from server errors. Invalid input gets 400, unauthenticated gets 401, forbidden gets 403, conflicts get 409, rate limits get 429, and dependency or server failures are 5xx.
```

### Timeouts And Retries

A timeout limits how long your service waits for another system. A retry tries again after a failure that may be temporary.

Retries are useful only when the operation is safe to repeat or has been made safe using idempotency. For example, retrying a read request is usually fine. Retrying a payment or order creation without an idempotency key can create duplicates.

Good interview answer:

```text
I would set a deadline for the whole request, then smaller timeouts for each dependency call. I would retry only transient failures, use exponential backoff with jitter, and only retry writes if they are idempotent.
```

Warning: retries increase load during an outage. Always use a max attempt count, backoff, jitter, and a total deadline.

### Idempotency

Idempotency means the same request can be safely repeated and still produce one logical result.

For order creation, the client sends an `Idempotency-Key` or `client_order_id`. The backend stores that key, a hash of the request payload, and the created order/result. If the client retries with the same key and same payload, return the original result. If the same key is reused with a different payload, return `409 Conflict`.

Good interview answer:

```text
For create-order, I would require an idempotency key. In one transaction, I would store the key, payload hash, and result. Duplicate retries return the original response. Same key with a different payload returns 409.
```

### Pagination

Large list APIs should not return unlimited rows. Pagination splits results into pages.

`OFFSET` pagination is simple but becomes slow for deep pages because the database still has to skip many rows. It can also behave badly if new rows are inserted while the user is paging.

Cursor pagination uses the last item from the previous page as the starting point for the next page. For orders, a stable cursor can be `(created_at, id)`.

Good interview answer:

```text
I would sort by created_at and id, return a cursor based on the last row, and use that cursor to fetch the next page. This is faster and more stable than large OFFSET values.
```

### Indexes

An index is an extra data structure the database maintains so it can find rows faster. It is useful when it matches the way you filter, sort, or join data.

Example: if the API frequently queries orders by `account_id` and sorts by newest first, an index on `(account_id, created_at DESC, id DESC)` can help.

Indexes are not free. They use disk space and slow down writes because every insert/update may also update the index.

Warning: do not say "add indexes everywhere." Say "add indexes for real query patterns and confirm with `EXPLAIN ANALYZE`."

### Transactions

A transaction groups database operations so they either all succeed or all fail. This protects important rules, also called invariants.

Example: when creating an order, you may need to insert the order row and insert the idempotency record together. If only one succeeds, the system can become inconsistent.

Good interview answer:

```text
I would use a transaction around the state that must change together. I would keep the transaction short and avoid slow external calls inside it.
```

### Queues And Workers

A queue lets the API accept work quickly and process it later in a worker. This helps when work is slow, bursty, or can be retried.

Example: the API stores an order request, then a worker sends it to an exchange. The queue protects the API from waiting on a slow exchange call.

Queues add new responsibilities: monitor queue age, retry failed jobs carefully, make handlers idempotent, and send permanently failing messages to a dead-letter queue.

Warning: queues improve reliability only if workers are idempotent and queue lag is monitored.

### Logs, Metrics, And Traces

Logs describe individual events. They are useful for answering "what happened to this request?"

Metrics are numbers over time. They are useful for alerts and dashboards, such as error rate, p99 latency, queue lag, and DB pool wait time.

Traces show the path of one request across services. They are useful for finding where time was spent.

Good interview answer:

```text
I would use metrics to detect the problem, traces to locate the slow dependency, and logs with request IDs to understand the specific failed request.
```

### Connection Pools

Opening a new DB connection for every request is expensive. A connection pool keeps a limited number of open connections and reuses them.

Pools also protect the database by limiting how many concurrent DB operations one service can run. If the pool is too small, requests wait. If it is too large across many app replicas, the database can be overloaded.

Good interview answer:

```text
I would size the pool based on DB capacity, number of service replicas, query latency, and traffic. I would monitor pool wait time because it shows whether requests are stuck waiting for DB connections.
```

### Horizontal Scaling

Horizontal scaling means running more app instances behind a load balancer.

For this to work well, API servers should be stateless. Shared state should live in a database, cache, queue, or external session store. After scaling the app layer, bottlenecks often move to the database, cache, downstream APIs, or connection pools.

Good interview answer:

```text
I would keep API instances stateless, put shared state outside the process, use health checks behind a load balancer, and watch DB/cache capacity as traffic grows.
```

### Trading-System Specific State

In trading systems, do not treat "request sent" as the same thing as "request accepted." A timeout also does not prove failure. The exchange may have received the request but the response may have been lost.

Good interview answer:

```text
I would model order states explicitly: created, risk_checked, sent, acknowledged, rejected, partially_filled, filled, cancel_requested, cancelled. After disconnects or timeouts, I would reconcile with the exchange before assuming the final state.
```

Warning: a cancel request is not a cancel confirmation. Always wait for confirmed state or reconcile.

---

## Top Interview Questions With Simple Answers

### 1. How would you design an idempotent order creation API?

Require an `Idempotency-Key` or `client_order_id`. Store the key, payload hash, and response in the database. If the same request is retried, return the stored response. If the same key is used with a different payload, return `409`.

### 2. How would you debug a slow API endpoint?

Start with metrics: request rate, p50/p95/p99 latency, error rate, DB time, dependency time, pool wait time, and recent deploys. Then use traces and logs to identify whether the time is spent in app code, database, cache, queue, or another service.

### 3. Why is cursor pagination better than `OFFSET` for large tables?

With `OFFSET`, the database may scan and skip many rows before returning the page. With a cursor, the database can continue from the last seen row using an indexed order, which is faster and more stable when data changes.

### 4. How would you prevent duplicate orders after a client timeout?

Use idempotency keys and store the result of the first request. If the client retries, the backend returns the original result instead of creating another order. If the request reached the exchange but the response was lost, reconcile by client order ID.

### 5. How would you design a rate limiter?

Choose a key such as user ID, API key, IP, account, or route. Use token bucket or sliding window. Store counters in Redis with atomic updates. Return `429` with retry guidance when the limit is exceeded.

### 6. How do you make worker processing reliable?

Use a durable queue, idempotent job IDs, retry with backoff, max attempt count, and a dead-letter queue. Monitor oldest message age, retry count, failure rate, and worker health.

### 7. How would you safely deploy a risky backend change?

Use a feature flag or canary rollout, watch dashboards and alerts, keep a rollback plan, and make database/message changes backward compatible while old and new versions run together.

### 8. How would you monitor a backend service?

Monitor request rate, error rate, latency, saturation, DB pool wait, dependency latency, queue lag, worker failures, and business metrics. Use logs with request IDs and traces for slow requests.

---

## Mini Coding Exercises

### 1. Idempotent Order Create

Problem: create an order safely when the client may retry after a timeout.

```python
import hashlib
import json


idempotency_store = {}
orders = []


def payload_hash(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def create_order(idempotency_key: str, payload: dict) -> dict:
    current_hash = payload_hash(payload)

    if idempotency_key in idempotency_store:
        saved = idempotency_store[idempotency_key]
        if saved["payload_hash"] != current_hash:
            return {"status": 409, "error": "same key used with different payload"}
        return saved["response"]

    order = {
        "id": len(orders) + 1,
        "symbol": payload["symbol"],
        "qty": payload["qty"],
        "status": "created",
    }
    orders.append(order)

    response = {"status": 201, "order": order}
    idempotency_store[idempotency_key] = {
        "payload_hash": current_hash,
        "response": response,
    }
    return response


print(create_order("abc-1", {"symbol": "NIFTY", "qty": 10}))
print(create_order("abc-1", {"symbol": "NIFTY", "qty": 10}))
print(create_order("abc-1", {"symbol": "BANKNIFTY", "qty": 10}))
```

Output:

```text
{'status': 201, 'order': {'id': 1, 'symbol': 'NIFTY', 'qty': 10, 'status': 'created'}}
{'status': 201, 'order': {'id': 1, 'symbol': 'NIFTY', 'qty': 10, 'status': 'created'}}
{'status': 409, 'error': 'same key used with different payload'}
```

Justification: the second call does not create a duplicate order because the same idempotency key returns the stored response. The third call is rejected because the client reused the same key for a different operation.

In production, the store should be a database table with a unique constraint on the idempotency key, and the order insert plus idempotency insert should happen in one transaction.

### 2. Cursor Pagination

Problem: fetch the next page of orders without using a large `OFFSET`.

```python
from datetime import datetime


orders = [
    {"id": 5, "created_at": datetime(2026, 1, 1, 10, 4), "symbol": "A"},
    {"id": 4, "created_at": datetime(2026, 1, 1, 10, 3), "symbol": "B"},
    {"id": 3, "created_at": datetime(2026, 1, 1, 10, 2), "symbol": "C"},
    {"id": 2, "created_at": datetime(2026, 1, 1, 10, 1), "symbol": "D"},
    {"id": 1, "created_at": datetime(2026, 1, 1, 10, 0), "symbol": "E"},
]


def get_page(limit: int, cursor: tuple | None = None) -> tuple[list[dict], tuple | None]:
    if cursor is None:
        page = orders[:limit]
    else:
        cursor_created_at, cursor_id = cursor
        page = [
            order
            for order in orders
            if (order["created_at"], order["id"]) < (cursor_created_at, cursor_id)
        ][:limit]

    next_cursor = None
    if page:
        last = page[-1]
        next_cursor = (last["created_at"], last["id"])

    return page, next_cursor


page1, cursor1 = get_page(limit=2)
page2, cursor2 = get_page(limit=2, cursor=cursor1)

print([order["id"] for order in page1], cursor1)
print([order["id"] for order in page2], cursor2)
```

Output:

```text
[5, 4] (datetime.datetime(2026, 1, 1, 10, 3), 4)
[3, 2] (datetime.datetime(2026, 1, 1, 10, 1), 2)
```

Equivalent SQL:

```sql
SELECT id, created_at, symbol, status
FROM orders
WHERE account_id = :account_id
  AND (
    :cursor_created_at IS NULL
    OR (created_at, id) < (:cursor_created_at, :cursor_id)
  )
ORDER BY created_at DESC, id DESC
LIMIT :limit;
```

Justification: the cursor remembers the last row from the previous page. The next query asks for rows older than that row, so the database can use the sorted index instead of skipping many rows.

### 3. Retry With Timeout, Backoff, And Jitter

Problem: retry a temporary failure without retrying forever.

```python
import asyncio
import random
import time


class TemporaryError(Exception):
    pass


async def retry_async(func, *, attempts: int, total_timeout: float):
    start = time.monotonic()

    for attempt in range(1, attempts + 1):
        remaining = total_timeout - (time.monotonic() - start)
        if remaining <= 0:
            raise TimeoutError("total retry deadline exceeded")

        try:
            return await asyncio.wait_for(func(), timeout=remaining)
        except TemporaryError:
            if attempt == attempts:
                raise

            delay = min(0.1 * (2 ** (attempt - 1)), remaining)
            delay += random.uniform(0, delay / 2)
            await asyncio.sleep(delay)


counter = {"calls": 0}


async def flaky_call():
    counter["calls"] += 1
    if counter["calls"] < 3:
        raise TemporaryError("dependency temporarily failed")
    return "success"


async def main():
    result = await retry_async(flaky_call, attempts=4, total_timeout=2.0)
    print(result)
    print(counter["calls"])


asyncio.run(main())
```

Output:

```text
success
3
```

Justification: the call failed twice, then succeeded on the third attempt. The wrapper has a total timeout, max attempts, and backoff so it cannot loop forever or hammer the dependency.

Warning: retry only transient errors. Do not retry a non-idempotent write unless you have an idempotency key or another deduplication mechanism.

### 4. Token Bucket Rate Limiter

Problem: allow short bursts but enforce an average request rate.

```python
import time


class TokenBucket:
    def __init__(self, capacity: int, refill_per_second: float):
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.tokens = capacity
        self.updated_at = time.monotonic()

    def allow(self) -> bool:
        now = time.monotonic()
        elapsed = now - self.updated_at
        self.updated_at = now

        self.tokens = min(
            self.capacity,
            self.tokens + elapsed * self.refill_per_second,
        )

        if self.tokens >= 1:
            self.tokens -= 1
            return True

        return False


bucket = TokenBucket(capacity=2, refill_per_second=1)

print(bucket.allow())
print(bucket.allow())
print(bucket.allow())
time.sleep(1.1)
print(bucket.allow())
```

Output:

```text
True
True
False
True
```

Justification: the first two requests are allowed because the bucket starts full. The third is rejected because no token remains. After waiting, one token is refilled and the next request is allowed.

In production, keep the bucket in Redis and update it atomically, usually with Lua, because multiple app instances may check the same user at the same time.

### 5. Worker With Retry And Dead-Letter Queue

Problem: process jobs reliably and isolate jobs that keep failing.

```python
from collections import deque


queue = deque([
    {"id": "job-1", "payload": "ok", "attempts": 0},
    {"id": "job-2", "payload": "bad", "attempts": 0},
])
processed_ids = set()
dead_letter_queue = []


def handle(job: dict) -> None:
    if job["id"] in processed_ids:
        return

    if job["payload"] == "bad":
        raise ValueError("invalid payload")

    processed_ids.add(job["id"])


while queue:
    job = queue.popleft()

    try:
        handle(job)
        print(f"processed {job['id']}")
    except Exception as exc:
        job["attempts"] += 1
        if job["attempts"] >= 3:
            dead_letter_queue.append({"job": job, "reason": str(exc)})
            print(f"sent {job['id']} to DLQ")
        else:
            queue.append(job)
            print(f"retrying {job['id']}")

print(dead_letter_queue)
```

Output:

```text
processed job-1
retrying job-2
retrying job-2
sent job-2 to DLQ
[{'job': {'id': 'job-2', 'payload': 'bad', 'attempts': 3}, 'reason': 'invalid payload'}]
```

Justification: successful jobs are marked processed, temporary failures are retried, and a permanently bad job is moved to the dead-letter queue after max attempts. This prevents one bad message from blocking the system forever.

Warning: production workers should use durable queues, visibility timeouts, idempotent job IDs, retry delay/backoff, and metrics for queue age and failures.

### 6. Slow Query Investigation

Problem: an endpoint slows from `50 ms` to `2 s` after the table grows.

Good answer:

```text
I would first check whether the slowdown is in app code, database, cache, or a dependency.
If DB time increased, I would run EXPLAIN ANALYZE for the query.
I would look for a sequential scan, missing index, bad join order, too many rows returned, or deep OFFSET pagination.
Then I would add a targeted index or rewrite the query and roll it out carefully.
```

Example query:

```sql
EXPLAIN ANALYZE
SELECT id, created_at, symbol, status
FROM orders
WHERE account_id = 42
ORDER BY created_at DESC, id DESC
LIMIT 50;
```

Possible fix:

```sql
CREATE INDEX CONCURRENTLY idx_orders_account_created_id
ON orders (account_id, created_at DESC, id DESC);
```

Justification: the index matches both the filter and the sort order. `CONCURRENTLY` avoids taking a heavy lock during index creation in PostgreSQL, which matters on a large production table.

---

## Production Debugging Scenarios

### API p99 Latency Spikes

First compare p50, p95, and p99 by endpoint and instance. If only p99 is bad, a small number of requests are very slow. Check DB pool wait time, slow queries, downstream latency, queue depth, CPU, memory, and recent deploys.

Good answer:

```text
I would split the request time into app, DB, cache, queue, and downstream time. Then I would mitigate based on the bottleneck: rollback a bad deploy, reduce traffic, add caching, tune a query, or shed non-critical work.
```

### Duplicate Orders

Search by `client_order_id`, `idempotency_key`, request ID, and exchange order ID. Compare API logs, DB rows, worker logs, and exchange acknowledgements.

Good answer:

```text
I would find whether the duplicate was created before sending to the exchange or after exchange submission. Then I would fix the boundary with unique constraints, idempotency persistence, and reconciliation by client order ID.
```

### Queue Lag Increasing

Queue lag means work is arriving faster than workers can finish it. Check worker errors, retry counts, DLQ size, downstream latency, CPU, and whether one bad message is being retried repeatedly.

Good answer:

```text
I would scale workers only after checking that the downstream system can handle more load. If failures are causing retries, I would separate bad messages and fix the root cause instead of blindly adding workers.
```

### Redis Memory High

Check key patterns, TTL coverage, value sizes, eviction count, and high-cardinality keys. If Redis is used as a cache, decide what can be evicted safely. If it stores important state, move durable data to a database or queue.

Good answer:

```text
I would identify which keys consume memory, add missing TTLs, reduce large values, and make sure Redis is not being used as the only durable source of truth.
```

### Database Deadlocks

Deadlocks happen when transactions wait on each other in a cycle. Common causes are updating rows in different order, long transactions, missing indexes, and many workers touching the same entities.

Good answer:

```text
I would inspect DB deadlock logs, standardize lock order, keep transactions short, add needed indexes, and retry safe transactions with backoff.
```

### Exchange Disconnect

After a disconnect, local state may be stale. Stop unsafe actions if needed, reconnect with backoff, replay from the last known sequence, and reconcile open orders and fills.

Good answer:

```text
I would not assume orders failed just because the connection dropped. I would mark the feed stale, reconnect, replay missing data, reconcile with the exchange, and only then resume normal processing.
```

---

## System Design Answer Templates

### Design A Trading Order API

Start with the API: create order, get order, cancel order, list orders. Add authentication and authorization. Validate symbol, quantity, price, account, and risk limits. Store the order in the database with an idempotency key or client order ID.

Then model order states clearly: created, risk checked, sent, acknowledged, rejected, partially filled, filled, cancel requested, and cancelled. Add audit logs, metrics, and reconciliation jobs.

Good answer:

```text
The important part is that order creation, idempotency, state transitions, and reconciliation are explicit. I would never rely only on an in-memory flag for order state.
```

### Design Internal Operations Dashboard Backend

The dashboard mostly reads data, so design read APIs with filtering, sorting, and cursor pagination. Add role-based access control because internal tools can still be dangerous.

Avoid heavy queries directly on the primary database. Use read replicas, precomputed views, caching for safe reference data, and audit logs for admin actions.

Good answer:

```text
I would optimize the dashboard for safe reads, strict permissions, and auditability. Admin actions should have request IDs and logs because they can affect production state.
```

### Design Exchange Connectivity Service

This service manages sessions with the exchange. It needs heartbeats, reconnect logic, sequence numbers, message replay, order state persistence, and reconciliation.

It should also have backpressure and a kill switch. If the exchange state is unknown, the system should degrade safely instead of continuing blindly.

Good answer:

```text
The key point is state correctness. On gaps, disconnects, or timeouts, I would mark state uncertain, replay or resync, reconcile orders, and then resume.
```

### Design Distributed Rate Limiter

Pick the limit key: user, API key, IP, account, route, or a combination. Choose the algorithm: token bucket for bursts or sliding window for stricter limits.

Use Redis for shared counters across app instances. Updates must be atomic so two servers cannot both allow the same last token.

Good answer:

```text
I would use Redis with an atomic Lua script, return 429 when the limit is exceeded, include retry guidance, and monitor allowed/blocked counts and Redis errors.
```

### Design Reliable Worker System

Use a durable queue and make every job idempotent. Track attempts, use retry with backoff, and send permanently failing jobs to a dead-letter queue with the reason and original payload.

Monitor queue age, attempts, failures, worker restarts, and downstream latency.

Good answer:

```text
The API should not assume a queued job succeeded. Workers need idempotency, retries, DLQ handling, and metrics so delayed or failed work is visible.
```

### Design Monitoring For A Backend Service

Monitor user-facing symptoms first: request rate, error rate, and latency. Then monitor saturation: CPU, memory, DB pool wait, queue lag, and dependency latency.

Use structured logs with request IDs and traces for slow paths. Alerts should be actionable and tied to user impact.

Good answer:

```text
I would alert on symptoms like high error rate, high p99 latency, and queue age. Dashboards can include deeper internals, but alerts should wake people only for real user or business impact.
```

---

## One-Hour Before Interview Revision

- Every dependency call needs a timeout.
- Retry only transient failures, with max attempts, backoff, jitter, and a deadline.
- Retryable writes need idempotency.
- Important requests need a request ID or correlation ID.
- Cursor pagination is usually better than deep `OFFSET`.
- Indexes speed matching reads but cost storage and write time.
- Transactions protect state that must change together; keep them short.
- Async Python helps I/O-heavy work, not CPU-heavy work.
- The GIL does not protect business rules from race conditions.
- Queues decouple work but require idempotent workers and lag monitoring.
- Redis is fast shared state, but durable source-of-truth data usually belongs in a database or durable queue.
- In trading systems, timeout means unknown until you reconcile.

---

## Final Mental Model

For almost every backend or HFT systems answer:

```text
State the contract.
Name the stored state.
Walk through the normal flow.
Explain failures and unknown states.
Add timeout, retry, idempotency, transaction, and observability.
Explain how you would debug and safely roll back.
```
