# Data, Caching, And Persistence

Tags: #backend #databases #sql #redis #caching #transactions #interview #production

Interview lens: connect every data choice to latency, correctness, contention, and failure recovery.

---

## Connection Pooling

### Concept

Connection pools reuse expensive connections to databases, Redis, and HTTP services.

### Why It Matters In Backend Systems

Opening a connection per request wastes CPU, adds latency, and can exhaust database or kernel resources. Pools make access predictable under load.

### Production Relevance

- DB pools limit concurrent database work from each app instance.
- HTTP pools reuse TCP/TLS connections to downstream services.
- Pool exhaustion is an important latency and incident signal.

### Database Pool Example

```python
import asyncpg

async def create_pool():
    return await asyncpg.create_pool(
        dsn="postgresql://orders:secret@db/orders",
        min_size=2,
        max_size=20,
        command_timeout=0.5,
    )

async def fetch_order(pool, order_id: str):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT id, symbol, status FROM orders WHERE id = $1",
            order_id,
        )
```

### HTTP Pool Example

```python
import httpx

client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=0.1, read=0.4, write=0.2, pool=0.1),
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
)
```

### Interview Traps

- Setting huge pools per instance and overwhelming the DB after scaling out.
- Not closing connections on shutdown.
- Holding DB connections while waiting on external services.
- No timeout for pool acquisition.

### Performance Considerations

- Larger pools do not automatically improve throughput.
- Too small: requests wait for connections.
- Too large: DB context switching and lock contention increase.
- Measure pool wait time separately from query time.

### Scalability And Reliability

- Total DB connections = app instances x pool size.
- Pool limits provide backpressure.
- Graceful shutdown should stop accepting requests and drain borrowed connections.

### Common Mistakes

- One global connection created lazily without lifecycle management.
- Long transactions holding pooled connections.
- No metrics for active/idle/waiting connections.

### Quick Revision

- Pools improve reuse and protect dependencies.
- Tune pools against database capacity, not only app traffic.

---

## Caching Basics

### Concept

Caching stores computed or fetched data closer to the caller to reduce latency and backend load.

### Why It Matters In Backend Systems

Backend APIs often serve repeated reads: reference data, account settings, risk config, market metadata, exchange status, and dashboards.

### Production Relevance

- Cache-aside is common: read cache, on miss read DB, then populate cache.
- TTL bounds staleness and memory growth.
- Invalidation is harder than population.
- Not all data is safe to cache.

### Patterns

| Pattern | How it works | Tradeoff |
|---|---|---|
| Cache-aside | App reads/writes cache explicitly | Simple, misses hit DB |
| Read-through | Cache layer loads on miss | Cleaner callers, more cache complexity |
| Write-through | Write DB and cache together | Fresher cache, write latency |
| Write-behind | Cache now, DB later | Fast writes, data-loss risk |

### Cache-Aside Example

```python
import json

async def get_risk_limits(account_id: str) -> dict:
    key = f"risk_limits:{account_id}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)

    limits = await db.fetch_risk_limits(account_id)
    await redis.set(key, json.dumps(limits), ex=30)
    return limits
```

### Interview Traps

- Saying "add Redis" without discussing invalidation/staleness.
- Caching permission checks or risk limits with unsafe TTLs.
- No stampede protection during cache misses.
- No plan for Redis failure.

### Performance Considerations

- Caches reduce read latency and DB load.
- Cache serialization/deserialization can be significant in Python.
- Large cached values hurt network and memory.
- Stampedes happen when many requests miss at once.

### Scalability And Reliability

- Cache outages should not necessarily take down the product.
- Stale data can be worse than slow data in trading/risk systems.
- Use short TTLs or explicit invalidation for sensitive state.

### Common Mistakes

- No namespace/version in keys.
- Caching `None` incorrectly and causing repeated DB misses.
- Unbounded key cardinality.

### Quick Revision

- Caching trades freshness for latency and load reduction.
- Always discuss invalidation, TTL, stampede, and fallback.

---

## Redis Basics

### Concept

Redis is an in-memory data store used for caching, counters, rate limits, locks, pub/sub, queues, and ephemeral coordination.

### Why It Matters In Backend Systems

Redis is often the low-latency shared state layer between stateless services. It is useful but easy to misuse as a permanent database.

### Production Relevance

- Cache frequently read data.
- Store idempotency records with TTL.
- Implement atomic counters/rate limits.
- Publish lightweight events.
- Coordinate simple locks with expiration.

### Backend Examples

```python
# Idempotency result cache
async def get_or_create_order(key: str, payload_hash: str):
    existing = await redis.hgetall(f"idempotency:{key}")
    if existing:
        if existing["payload_hash"] != payload_hash:
            raise Conflict("same key used with different payload")
        return existing["response"]

    order = await create_order_in_db()
    await redis.hset(
        f"idempotency:{key}",
        mapping={"payload_hash": payload_hash, "response": order.json()},
    )
    await redis.expire(f"idempotency:{key}", 24 * 60 * 60)
    return order
```

```python
# Simple pub/sub notification
await redis.publish("exchange-status", '{"venue":"NASDAQ","status":"down"}')
```

### Interview Traps

- Using Redis locks without TTL.
- Assuming Redis pub/sub is durable.
- Treating Redis as strongly consistent permanent storage.
- Storing huge objects and causing memory pressure.

### Performance Considerations

- Redis is fast, but network round trips still matter.
- Pipeline batches of independent commands.
- Avoid blocking commands on shared Redis.
- Watch memory eviction policy and hot keys.

### Scalability And Reliability

- Redis can become a central bottleneck or SPOF.
- Cluster/sharding changes command guarantees.
- Decide fail-open vs fail-closed for auth/rate-limit/cache use cases.

### Common Mistakes

- No key TTLs for ephemeral data.
- No key naming convention.
- No monitoring for memory, evictions, latency, and connection count.

### Quick Revision

- Redis is excellent for ephemeral low-latency shared state.
- It is not a magic durable queue or relational database replacement.

---

## Database Indexing

### Concept

Indexes are data structures that speed reads by maintaining searchable order, commonly B-trees in relational databases.

### Why It Matters In Backend Systems

Most backend latency problems eventually involve slow queries, missing indexes, poor selectivity, or queries that worked in staging but fail on production data size.

### Production Relevance

- Index common filters, joins, and ordering patterns.
- Use composite indexes matching query shape.
- Measure with `EXPLAIN ANALYZE`.
- Remember indexes slow writes and consume storage.

### SQL Example

```sql
CREATE INDEX idx_orders_account_status_created
ON orders (account_id, status, created_at DESC);

EXPLAIN ANALYZE
SELECT id, symbol, status, created_at
FROM orders
WHERE account_id = 'acct-123'
  AND status = 'OPEN'
ORDER BY created_at DESC
LIMIT 100;
```

### Interview Traps

- Saying every column should be indexed.
- Ignoring write penalties.
- Missing index order for composite indexes.
- Assuming an index helps low-selectivity predicates like `status = 'ACTIVE'` alone.

### Performance Considerations

- B-tree indexes help equality/range/order queries.
- Composite index order matters.
- Covering indexes can avoid table lookups.
- Too many indexes slow inserts/updates/deletes.

### Scalability And Reliability

- Index creation on huge tables needs careful rollout.
- Concurrent index builds reduce locking but still consume resources.
- Slow queries can exhaust app pools and create cascading latency.

### Common Mistakes

- Using `OFFSET` pagination on large tables.
- Wrapping indexed columns in functions in `WHERE`.
- No query plan review before production migrations.

### Quick Revision

- Index for real query patterns, not theoretical fields.
- Always mention `EXPLAIN ANALYZE`, selectivity, and write cost.

---

## SQL Joins

### Concept

Joins combine rows from related tables.

| Join | Meaning | Practical use |
|---|---|---|
| `INNER JOIN` | Only matching rows | Orders with valid accounts |
| `LEFT JOIN` | All left rows plus matches | Orders even if optional fills missing |
| `RIGHT JOIN` | All right rows plus matches | Less common; can usually rewrite |
| `FULL JOIN` | All rows from both sides | Reconciliation/diff reports |

### Why It Matters In Backend Systems

Joins are common in APIs, reports, reconciliation, and admin tooling. Bad joins create wrong results or expensive queries.

### Production Examples

```sql
-- Orders with account names
SELECT o.id, o.symbol, o.status, a.name
FROM orders o
INNER JOIN accounts a ON a.id = o.account_id
WHERE o.created_at >= now() - interval '1 day';
```

```sql
-- Find orders without fills yet
SELECT o.id, o.symbol
FROM orders o
LEFT JOIN fills f ON f.order_id = o.id
WHERE f.order_id IS NULL;
```

```sql
-- Reconcile internal vs exchange order IDs
SELECT i.client_order_id, e.exchange_order_id
FROM internal_orders i
FULL JOIN exchange_orders e
  ON e.client_order_id = i.client_order_id
WHERE i.client_order_id IS NULL OR e.client_order_id IS NULL;
```

### Interview Traps

- Putting a right-table condition in `WHERE` after a `LEFT JOIN`, accidentally turning it into an inner join.
- Joining on non-indexed or non-unique columns.
- Not handling duplicate rows from one-to-many relationships.

### Performance Considerations

- Index join keys.
- Filter early where possible.
- Watch join cardinality.
- Avoid huge joins in latency-sensitive request paths if precomputation is better.

### Scalability And Reliability

- Analytical joins can overload transactional databases.
- Read replicas help but add replication lag.
- Incorrect joins can silently corrupt reports and operational decisions.

### Common Mistakes

- Selecting `*` from joined tables.
- No aliases in complex queries.
- Ignoring null behavior.

### Quick Revision

- Joins answer relationship questions; join type controls missing-row behavior.
- Always think about cardinality, indexes, and nulls.

---

## Transactions

### Concept

Transactions group database operations into an atomic unit. ACID means atomicity, consistency, isolation, and durability.

### Why It Matters In Backend Systems

Order creation, idempotency, risk reservation, account updates, and worker state transitions must not be half-applied.

### Production Relevance

- Use transactions for multi-step state changes.
- Keep transactions short.
- Use constraints to enforce invariants.
- Understand isolation and races.

### SQL Example

```sql
BEGIN;

INSERT INTO idempotency_keys (key, payload_hash, created_at)
VALUES (:key, :payload_hash, now());

INSERT INTO orders (id, account_id, symbol, quantity, status)
VALUES (:order_id, :account_id, :symbol, :quantity, 'PENDING');

UPDATE accounts
SET reserved_cash = reserved_cash + :notional
WHERE id = :account_id
  AND cash_balance - reserved_cash >= :notional;

COMMIT;
```

If the final update affects zero rows, rollback and reject for insufficient funds.

### Isolation Levels

| Level | Prevents | Still allows |
|---|---|---|
| Read committed | Dirty reads | Non-repeatable reads, phantoms |
| Repeatable read | Non-repeatable reads | Some phantom/write-skew cases depending on DB |
| Serializable | Most anomalies | More retries/contention |

### Interview Traps

- Assuming transactions solve all distributed consistency problems.
- Doing external HTTP calls inside DB transactions.
- Holding locks while doing slow work.
- Ignoring unique constraints for idempotency.

### Performance Considerations

- Long transactions hold locks and block vacuum/cleanup.
- Higher isolation can reduce concurrency.
- Retrying serialization failures must be safe.

### Scalability And Reliability

- Single-database transactions are strong and practical.
- Cross-service transactions are hard; use outbox/sagas/compensation.
- Constraints are reliable guards against race conditions.

### Common Mistakes

- Read-check-write without lock or conditional update.
- No rollback path on partial failure.
- No retry handling for deadlocks/serialization failures.

### Quick Revision

- Use transactions to protect invariants.
- Keep them short, enforce constraints, and avoid external calls inside them.
