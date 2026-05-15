# Concurrency, Distributed Systems, And Scaling

Tags: #backend #concurrency #distributed-systems #queues #scaling #load-balancing #idempotency #interview

Interview lens: name the shared state, the failure mode, and the mechanism that preserves correctness under concurrency and retries.

---

## Concurrency Problems

### Concept

Concurrency bugs happen when multiple threads, tasks, processes, or services interact with shared state without safe coordination.

### Why It Matters In Backend Systems

Production backends run many requests and workers at once. Race conditions can duplicate orders, lose updates, over-reserve balances, or process the same job twice.

### Production Relevance

- Python's GIL does not make business logic race-free.
- Async code can still race around awaited operations.
- Database locks/constraints are often better than app-only locks.
- Distributed systems need idempotency because exact-once execution is rare.

### Python Race Example

```python
import asyncio

positions: dict[str, int] = {"AAPL": 0}
lock = asyncio.Lock()

async def apply_fill(symbol: str, quantity: int):
    async with lock:
        current = positions.get(symbol, 0)
        await asyncio.sleep(0)  # context switch would expose unsafe code
        positions[symbol] = current + quantity
```

For real production balances, prefer database transactions or a single-writer event stream over process-local locks.

### SQL Lost Update Fix

```sql
UPDATE accounts
SET reserved_cash = reserved_cash + :amount
WHERE id = :account_id
  AND cash_balance - reserved_cash >= :amount;
```

Check affected row count. This is atomic and avoids read-check-write races.

### Interview Traps

- Saying the GIL prevents races.
- Locking only in one app instance while multiple instances run.
- Assuming async means parallelism.
- Ignoring deadlocks and lock ordering.

### Performance Considerations

- Locks serialize work and can increase tail latency.
- Fine-grained locks improve concurrency but are harder to reason about.
- Atomic DB updates are often faster and safer than application read-modify-write.

### Scalability And Reliability

- Local locks do not protect distributed state.
- Single-writer designs simplify correctness for hot entities.
- Deadlocks require retry logic and observability.

### Common Mistakes

- Shared mutable globals in web apps.
- Holding locks across network calls.
- No idempotency in workers.

### Quick Revision

- Identify shared state first.
- Use constraints, transactions, ownership, or queues to control concurrency.

---

## Queues And Workers

### Concept

Queues decouple request intake from background processing. Workers consume jobs asynchronously.

### Why It Matters In Backend Systems

Queues protect APIs from slow work, smooth bursts, isolate failures, and enable retryable processing.

### Production Relevance

- Use queues for emails, exports, reconciliation, exchange sync, post-trade processing, and slow integrations.
- Track queue depth, oldest message age, retry count, and dead-letter volume.
- Jobs must be idempotent because delivery is often at-least-once.

### Producer-Consumer Example

```python
import asyncio

queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=10_000)

async def enqueue_reconcile(account_id: str):
    await queue.put({"type": "reconcile_account", "account_id": account_id})

async def worker():
    while True:
        job = await queue.get()
        try:
            await reconcile_account(job["account_id"])
        except TransientError:
            await retry_later(job)
        except Exception:
            await dead_letter(job)
        finally:
            queue.task_done()
```

Production queues are usually Redis Streams, RabbitMQ, SQS, Kafka, Celery/RQ, or similar.

### Interview Traps

- Forgetting dead-letter queues.
- Retrying poison messages forever.
- Assuming queue success means downstream success.
- No idempotency key in jobs.

### Performance Considerations

- Queue lag is the key user-impact metric.
- Batch when throughput matters.
- Use bounded concurrency to protect dependencies.
- Large messages hurt broker memory and network.

### Scalability And Reliability

- More workers increase throughput until a downstream bottleneck.
- At-least-once delivery needs deduplication.
- DLQs preserve failed jobs for inspection instead of dropping them.

### Common Mistakes

- No visibility into retry attempts.
- Workers doing unbounded parallel work.
- Mixing high-priority and low-priority jobs in one queue.

### Quick Revision

- Queues decouple and absorb bursts, but introduce lag and retry/idempotency concerns.
- Monitor depth, age, retries, failures, and worker saturation.

---

## Distributed Systems Basics

### Concept

A distributed system is multiple networked components working together while facing partial failure, latency, independent deploys, and inconsistent views of state.

### Why It Matters In Backend Systems

Modern backend services depend on databases, caches, queues, proxies, auth systems, exchange gateways, monitoring pipelines, and other services.

### Production Relevance

- Networks fail, timeout, duplicate, and reorder.
- Replicas lag.
- Clocks drift.
- Deploys are rolling, so versions overlap.
- Dependencies can be slow without being fully down.

### Core Ideas

| Concept | Practical meaning |
|---|---|
| Replication | Copies improve read scale/availability but can lag |
| Consistency | All readers see the same state at the same time only with tradeoffs |
| Fault tolerance | Continue operating when parts fail |
| Coordination | Agreeing on ownership/leader/locks is hard |
| Backpressure | Slow intake before the system collapses |

### CAP Theorem Basics

Under network partition, a distributed system must choose between consistency and availability. In interviews, avoid overusing CAP; apply it to a real decision like "should order state reads come from primary or replica?"

### Interview Traps

- Saying "use microservices" without discussing failure boundaries.
- Assuming exactly-once delivery.
- Ignoring replication lag.
- Relying on wall-clock ordering for correctness.

### Performance Considerations

- Remote calls are much slower and less reliable than local calls.
- Fan-out multiplies latency and failure probability.
- Batching and caching reduce calls but introduce staleness.

### Scalability And Reliability

- Prefer simple service boundaries.
- Use timeouts, retries, circuit breakers, bulkheads, and queues.
- Design for partial degradation, not only full uptime.

### Common Mistakes

- No dependency timeout.
- No ownership for shared data.
- Synchronous call chains too deep.

### Quick Revision

- Distributed systems are about partial failure and coordination.
- Always discuss timeouts, retries, idempotency, and observability.

---

## Idempotency

### Concept

An operation is idempotent if repeating it has the same final effect as running it once.

### Why It Matters In Backend Systems

Clients retry after timeouts. Workers restart. Messages redeliver. Without idempotency, systems duplicate orders, charges, emails, or state transitions.

### Production Relevance

- Write APIs should accept idempotency keys.
- Persist the key, payload hash, status, and final response.
- Use unique constraints for correctness.
- Expire old keys after a defined window.

### Order API Example

```python
@app.post("/v1/orders", status_code=201)
async def create_order(
    body: OrderCreate,
    idempotency_key: str = Header(alias="Idempotency-Key"),
):
    payload_hash = hash_payload(body)
    async with db.transaction():
        existing = await db.fetch_idempotency(idempotency_key)
        if existing:
            if existing.payload_hash != payload_hash:
                raise HTTPException(status_code=409, detail="idempotency key reused with different payload")
            return existing.response

        order = await db.insert_order(body)
        await db.insert_idempotency_key(idempotency_key, payload_hash, order)
        return order
```

### Duplicate Request Handling

| Case | Response |
|---|---|
| Same key + same payload + completed | Return original result |
| Same key + different payload | `409 Conflict` |
| Same key + in progress | `202 Accepted` or retry-after response |
| Key expired | Treat as new request, depending on contract |

### Interview Traps

- Storing idempotency key after the side effect, leaving a race window.
- Using only in-memory dedupe.
- Not hashing/comparing payloads.
- Forgetting downstream side effects like exchange submission.

### Performance Considerations

- Idempotency records need indexes and TTL cleanup.
- Hot clients can create hot keys.
- Deduplication adds a read/write to critical paths.

### Scalability And Reliability

- Idempotency is essential for safe retries.
- Unique constraints are stronger than app-only checks.
- Client order IDs are common in trading systems for duplicate protection.

### Common Mistakes

- Assuming timeout means failure.
- Reusing idempotency keys across unrelated operations.
- No way to resume "in progress" operations.

### Quick Revision

- Idempotency makes retries safe.
- Store the key atomically with the state change.

---

## Horizontal Scaling

### Concept

Horizontal scaling adds more service instances instead of making one instance bigger.

### Why It Matters In Backend Systems

APIs, workers, and read-heavy services usually scale by running more replicas behind a load balancer or queue.

### Production Relevance

- Stateless services scale easiest.
- Shared state belongs in databases, caches, queues, or external stores.
- Scaling app instances can move the bottleneck to DB, Redis, or downstream APIs.

### Stateless Handler Example

```python
@app.get("/v1/orders/{order_id}")
async def get_order(order_id: str, user: User = Depends(require_user)):
    order = await db.fetch_order(order_id)
    authorize(user, order.account_id)
    return order
```

No per-user data is stored in process memory, so any instance can handle the request.

### Interview Traps

- Scaling stateless apps while ignoring the database.
- Storing sessions in local memory.
- Assuming autoscaling instantly fixes overload.
- No warmup/readiness behavior.

### Performance Considerations

- More instances can increase connection pressure.
- Cold starts and cache warmup affect latency.
- Load must be balanced evenly.

### Scalability And Reliability

- Use readiness checks so only healthy instances receive traffic.
- Use graceful shutdown to drain in-flight requests.
- Scale workers based on queue lag, not only CPU.

### Common Mistakes

- No per-instance resource limits.
- No backpressure when dependencies saturate.
- No capacity model for downstream services.

### Quick Revision

- Stateless services scale horizontally.
- Every scaling answer must identify the next bottleneck.

---

## Load Balancing Basics

### Concept

Load balancers distribute traffic across backend instances and remove unhealthy ones.

### Why It Matters In Backend Systems

They are central to high availability, rolling deploys, failover, and traffic distribution.

### Production Relevance

- Reverse proxies terminate TLS and route traffic.
- Health checks decide which instances receive traffic.
- Algorithms affect fairness and tail latency.
- Sticky sessions can hide statefulness problems.

### Algorithms

| Algorithm | Good for | Tradeoff |
|---|---|---|
| Round robin | Similar request cost | Can overload slow instances |
| Least connections | Long-lived/variable requests | Needs live connection tracking |
| Weighted | Unequal instance capacity | Requires correct weights |
| Consistent hashing | Cache locality/sticky routing | Uneven distribution risk |

### Nginx-Style Example

```nginx
upstream api_backend {
    least_conn;
    server api-1:8000 max_fails=3 fail_timeout=10s;
    server api-2:8000 max_fails=3 fail_timeout=10s;
}

server {
    location / {
        proxy_connect_timeout 100ms;
        proxy_read_timeout 1s;
        proxy_set_header X-Request-ID $request_id;
        proxy_pass http://api_backend;
    }
}
```

### Interview Traps

- Forgetting health checks.
- No timeout between proxy and app.
- Sticky sessions used because app stores local state.
- No connection draining during deploy.

### Performance Considerations

- Load balancer timeouts shape user-visible failures.
- TLS termination costs CPU.
- Uneven load increases p99 latency.

### Scalability And Reliability

- Multi-zone load balancing improves availability.
- Readiness probes protect new or degraded instances.
- Connection draining prevents dropped in-flight requests.

### Common Mistakes

- Liveness and readiness checks are identical.
- Health check endpoint does expensive dependency checks too frequently.
- No propagation of request IDs.

### Quick Revision

- Load balancers distribute traffic and enforce health.
- Mention algorithms, health checks, timeouts, and graceful deploys.
