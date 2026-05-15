# Backend Systems Final Revision

Tags: #backend #systems #hft #interview #revision #production

Use this file in the final day/hour before an interview. Answers should be practical: failure mode, tradeoff, production mitigation, and how you would debug it.

---

## Top 30 Most Likely Backend/System Interview Questions

1. How would you design an idempotent order creation API?
   - Answer: Use an `Idempotency-Key` or client order ID, store a payload hash and result atomically, reject same-key/different-payload with `409`, and return the original response for safe retries.
2. What is the difference between authentication and authorization?
   - Answer: Authentication proves who the caller is; authorization decides what that authenticated caller may do.
3. When should a backend return `400`, `401`, `403`, `404`, `409`, `429`, `500`, `503`, and `504`?
   - Answer: Use `400` for bad input, `401` unauthenticated, `403` forbidden, `404` missing resource, `409` conflict, `429` rate limited, `500` bug/unexpected failure, `503` unavailable/overloaded dependency, and `504` upstream timeout.
4. How do retries and timeouts interact in distributed systems?
   - Answer: Timeouts bound waiting; retries can recover transient failure, but each retry must fit within an end-to-end deadline and be safe for the operation.
5. Why are retry storms dangerous, and how do you prevent them?
   - Answer: Retry storms multiply load during outages; prevent them with backoff, jitter, retry budgets, circuit breakers, rate limits, and idempotency.
6. How would you design pagination for a large orders table?
   - Answer: Use stable ordering such as `(created_at, id)`, a cursor containing the last seen values, max page sizes, and deterministic filters.
7. Why is cursor pagination usually better than `OFFSET` pagination?
   - Answer: Cursor pagination avoids scanning/skipping large offsets and behaves better while rows are inserted or deleted.
8. How do database indexes work, and what are their tradeoffs?
   - Answer: Indexes are extra ordered data structures that speed lookups/sorts for matching query patterns but cost storage, writes, and maintenance.
9. How would you debug a slow API endpoint in production?
   - Answer: Check metrics first: p50/p99, errors, traffic, queue lag, DB/query timings, pool waits, dependency latency, CPU/memory, deploys, logs, and traces.
10. What metrics would you add to a Python backend service?
    - Answer: Add request rate, status/error rate, p95/p99 latency, queue depth/age, DB pool waits, dependency latency, worker failures, restarts, and business metrics like order rejects.
11. How do logs, metrics, and traces differ?
    - Answer: Metrics quantify trends and alert conditions; logs explain individual events; traces show request path and time across services.
12. What should go into a structured log for an order API?
    - Answer: Include timestamp, service, host, version, request ID, client/order IDs, user/account, endpoint, state transition, latency, status, error code, and sanitized context.
13. How do connection pools improve performance, and how can they fail?
    - Answer: Pools reuse expensive connections and cap concurrency; they fail when undersized, oversized, leaked, exhausted, or pointed at slow dependencies.
14. How would you choose the size of a DB connection pool?
    - Answer: Size pools from DB capacity, service replicas, expected concurrency, query latency, and timeout budgets; measure wait time and avoid exceeding DB connection limits.
15. How do transactions prevent race conditions?
    - Answer: Transactions group related reads/writes so invariants change atomically and concurrent updates cannot leave partial state.
16. What isolation-level issues can appear in backend systems?
    - Answer: Dirty reads, non-repeatable reads, phantom reads, lost updates, and write skew can appear depending on isolation level and access pattern.
17. How would you handle duplicate requests after client timeouts?
    - Answer: Reuse the idempotency key/client order ID, return stored result if the original completed, and reconcile if the first attempt reached an external system.
18. How would you design a distributed rate limiter?
    - Answer: Use shared storage such as Redis with atomic operations/Lua or a centralized limiter, define keys and windows carefully, and fail safely under store outage.
19. What is the token bucket algorithm?
    - Answer: Token bucket refills tokens at a steady rate up to a capacity; each request spends a token, allowing bursts while enforcing average rate.
20. How do queues improve backend reliability?
    - Answer: Queues decouple producers and consumers, buffer bursts, enable retries, and isolate failures, but require lag monitoring and idempotent handlers.
21. What are dead-letter queues and poison messages?
    - Answer: A DLQ stores messages that cannot be processed after retries; poison messages repeatedly fail due to bad payloads, bugs, or invalid state.
22. What is the difference between at-most-once, at-least-once, and exactly-once delivery?
    - Answer: At-most-once may drop messages, at-least-once may duplicate messages, and exactly-once is usually achieved as effectively-once behavior with idempotent processing and transactions.
23. How do you horizontally scale a stateless API?
    - Answer: Keep API servers stateless, put shared state in DB/cache/queue, use a load balancer, externalize sessions, and make deploys/health checks safe.
24. What bottlenecks appear after scaling app servers?
    - Answer: Bottlenecks move to DB, cache, queues, downstream APIs, connection pools, locks, hot partitions, and network limits.
25. How do load balancers decide where to send traffic?
    - Answer: Load balancers use algorithms like round-robin, least connections, hashing, or latency/health-aware routing, and should respect readiness checks.
26. How would you handle exchange disconnects and sequence gaps?
    - Answer: Mark feeds stale on disconnect/gap, reconnect with backoff, resubscribe, snapshot/replay missing data, and reconcile orders before trusting state.
27. Why is timeout not equal to failure in trading systems?
    - Answer: A timeout means no answer arrived before the deadline; the operation may have succeeded, failed, or still be in progress.
28. How would you deploy a risky backend change safely?
    - Answer: Use canaries, feature flags, backward-compatible schema/message changes, health checks, dashboards, alerts, and a tested rollback path.
29. What Linux commands would you use during a production incident?
    - Answer: Use `systemctl`, `journalctl`, `ps`, `top`, `ss`, `lsof`, `df`, `du`, `free`, `dmesg`, `curl`, `dig`, and log filtering with `grep`/`awk`/`jq`.
30. How would you design monitoring and alerting for a high-uptime backend service?
    - Answer: Define SLIs/SLOs, expose metrics, dashboards, structured logs, and traces, alert on user/business impact, include runbooks, and monitor dependencies plus saturation.

---

## One-Hour Before Interview Revision

- Every outbound dependency call needs a timeout.
- Every retryable write needs idempotency.
- Every important request needs a correlation/request ID.
- `4xx` means caller/request issue; `5xx` means server/dependency issue.
- Cursor pagination is safer than `OFFSET` for large/changing tables.
- Indexes speed reads but slow writes and consume storage.
- Transactions protect invariants; keep them short.
- The GIL does not prevent business-level races.
- Async helps IO concurrency, not CPU-bound Python.
- Queues decouple work but introduce lag, retries, and idempotency requirements.
- Redis is fast ephemeral shared state, not a default source of truth.
- Structured logs plus metrics plus traces are stronger than any one alone.
- Alert on symptoms: error rate, p99 latency, queue lag, exchange disconnects.
- Horizontal scaling moves bottlenecks to DB/cache/downstream services.
- In trading systems, timeout often means unknown; reconcile before assuming failure.

---

## Most Common Backend Engineering Mistakes

| Mistake | Production-safe answer |
|---|---|
| Retrying every failure | Retry transient failures with deadline, backoff, jitter, idempotency |
| No timeouts | Set connect/read/write/pool and end-to-end deadlines |
| Huge list endpoints | Use cursor pagination and maximum limits |
| No idempotency for writes | Persist idempotency key and response atomically |
| Local process state in scaled APIs | Store shared state externally |
| Too many DB connections | Size pools against DB capacity |
| Indexing everything | Index real query patterns and measure write cost |
| Logging secrets | Redact tokens/PII and log identifiers |
| No correlation IDs | Propagate request/order IDs across services |
| Infinite worker retries | Use retry budgets and DLQs |
| Ignoring queue lag | Alert on oldest message age and backlog |
| Treating Redis as durable | Use DB/queue for durable state |
| Blocking in async handlers | Use async clients or run blocking work elsewhere |
| External calls inside transactions | Keep transactions short and local |
| No rollback plan | Use canaries, feature flags, and monitored deploys |

---

## Quick HFT / Backend Production Engineering Tips

- Model order state explicitly; do not infer it from one field.
- Use client order IDs for duplicate detection and reconciliation.
- Treat `sent to exchange` and `acknowledged by exchange` as different states.
- A cancel request is not a cancel confirmation.
- Persist sequence numbers and detect gaps.
- Heartbeats should alert quickly but reconnect with backoff.
- Keep hot paths free of noisy logs, large allocations, and blocking calls.
- Monitor event age, not only processing throughput.
- Prefer bounded queues and backpressure over unlimited buffering.
- Use monotonic time for deadlines and elapsed-time measurements.
- Separate critical order paths from reporting/admin work.
- Have a clear degraded mode when exchange/risk state is unknown.

---

## Mini Backend Coding Exercises

### 1. Idempotent Order Create

Prompt: implement an order create handler that accepts `Idempotency-Key`, rejects key reuse with different payload, and returns the original result for duplicate retries.

Key points:

- Unique constraint on idempotency key.
- Payload hash comparison.
- DB transaction around idempotency record and order insert.
- `409 Conflict` for same key/different payload.

### 2. Cursor Pagination

Prompt: write SQL to fetch next page of orders sorted by `created_at DESC, id DESC`.

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

### 3. Retry Wrapper

Prompt: write an async retry wrapper with timeout, exponential backoff, jitter, and max attempts.

Must mention:

- Retry only transient exceptions.
- Respect total deadline.
- Add jitter.
- Do not retry non-idempotent writes unless made idempotent.

### 4. Rate Limiter

Prompt: implement token bucket rate limiting with Redis.

Must mention:

- Atomic update with Lua/transaction.
- TTL on bucket keys.
- `429` response with retry guidance.
- Fail-open/fail-closed decision.

### 5. Worker With DLQ

Prompt: process queue jobs with retries and dead-letter after max attempts.

Must mention:

- Idempotent job key.
- Retry count.
- Backoff.
- DLQ with reason and original payload.

### 6. Slow Query Investigation

Prompt: an endpoint slows from 50 ms to 2 s after data growth.

Answer shape:

- Check metrics and query timings.
- Run `EXPLAIN ANALYZE`.
- Look for missing index, bad selectivity, sequential scan, join explosion, `OFFSET`.
- Add targeted index or rewrite query.
- Roll out safely on large table.

---

## Real-World Production Debugging Scenarios

### Scenario 1: API p99 Latency Spikes

Likely causes:

- DB query regression.
- Connection pool exhaustion.
- Slow downstream dependency.
- Uneven load balancer distribution.
- Logging/serialization overhead.
- Deploy introduced blocking code.

Debug steps:

- Compare p50/p95/p99 by endpoint and instance.
- Split app time vs DB/cache/downstream time.
- Check pool wait time and queue depth.
- Inspect recent deploy/config changes.
- Mitigate with rollback, traffic shift, caching, or shedding non-critical traffic.

### Scenario 2: Duplicate Orders

Likely causes:

- Client retried after timeout.
- Missing idempotency key.
- Idempotency key stored after exchange send.
- Worker redelivered job.

Debug steps:

- Search by client order ID, request ID, and idempotency key.
- Compare API logs, DB rows, exchange acks.
- Identify whether duplicate was internal or exchange-side.
- Add unique constraints and atomic idempotency persistence.

### Scenario 3: Queue Lag Increasing

Likely causes:

- Worker errors/retries.
- Downstream dependency slow.
- Poison message blocking processing.
- Traffic spike.
- Insufficient worker concurrency.

Debug steps:

- Check oldest message age, retries, DLQ, worker CPU, downstream latency.
- Scale workers only if downstream can handle it.
- Separate poison messages and high-priority queues.

### Scenario 4: Redis Memory High

Likely causes:

- Missing TTL.
- Large values.
- High-cardinality keys.
- Cache stampede.
- Pub/sub misuse or queue backlog.

Debug steps:

- Inspect key patterns and TTL coverage.
- Check evictions and latency.
- Reduce value size, add TTLs, shard, or change cache policy.

### Scenario 5: Database Deadlocks

Likely causes:

- Transactions update rows in different order.
- Long transactions.
- Missing indexes causing wide locks.
- Concurrent workers touch same entities.

Debug steps:

- Inspect DB deadlock logs.
- Standardize lock order.
- Keep transactions short.
- Retry safe transactions with backoff.

### Scenario 6: Exchange Disconnect

Likely causes:

- Network issue.
- Heartbeat missed.
- Venue maintenance.
- Sequence gap.
- Authentication/session expiry.

Debug steps:

- Stop unsafe sends if state is unknown.
- Reconnect with backoff.
- Replay from last sequence.
- Reconcile open orders and fills.
- Alert operators with venue/session/account impact.

---

## Common Reliability / System Design Interview Scenarios

### Design A Trading Order API

Must include:

- AuthN/AuthZ.
- Validation and risk checks.
- Idempotency key/client order ID.
- Transactional order persistence.
- Async exchange submission if needed.
- Order state machine.
- Audit logs and reconciliation.
- Metrics for latency, rejects, duplicate keys, exchange errors.

### Design Internal Operations Dashboard Backend

Must include:

- Read-optimized APIs.
- Pagination/filtering/sorting.
- Role-based access control.
- Cache safe reference data.
- Avoid heavy queries on primary DB.
- Correlation IDs and audit logs for admin actions.

### Design Exchange Connectivity Service

Must include:

- Session lifecycle and heartbeats.
- Sequence numbers and replay.
- Reconnect/backoff.
- Persistent state transitions.
- Reconciliation jobs.
- Backpressure and kill switch.

### Design Distributed Rate Limiter

Must include:

- Key dimensions: user/API key/IP/account/route.
- Token bucket/sliding window.
- Redis atomic Lua update.
- Local fallback/cache.
- Fail-open/fail-closed tradeoff.
- `429` response and observability.

### Design Reliable Worker System

Must include:

- Durable queue.
- Idempotent jobs.
- Retry with backoff.
- DLQ.
- Visibility timeout/ack model.
- Worker concurrency limits.
- Metrics for queue age, attempts, failures.

### Design Monitoring For Backend Service

Must include:

- RED metrics: rate, errors, duration.
- Saturation: CPU, memory, pool wait, queue lag.
- Dependency metrics.
- Structured logs with request ID.
- Traces for slow paths.
- Actionable alerts and runbooks.

---

## Final Mental Model

For almost every backend/HFT systems answer:

```text
Define the contract.
Identify state and ownership.
Describe failure modes.
Add timeouts, retries, idempotency, and observability.
Protect dependencies with pools, limits, and backpressure.
Explain the production debugging path.
```
