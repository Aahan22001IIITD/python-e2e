# Latency Importance In Trading Systems

Tags: #latency #performance #hft #backend #observability #interview

Interview lens: latency is end-to-end time across network, application code, queues, serialization, storage, and exchange response. In trading systems, tail latency often matters more than average latency.

---

## Concept

Latency is the time between an input and the corresponding observable output.

Trading examples:

- Market data tick received -> strategy sees update.
- Order API request received -> order sent to exchange.
- Order sent to exchange -> acknowledgement received.
- Cancel requested -> exchange confirms cancel.
- Exchange fill received -> position/risk state updated.

Important distinction:

- p50 latency: normal path.
- p95/p99 latency: slow-path behavior under load or failure.
- max latency: worst cases, often caused by pauses, retries, locks, GC, I/O, or network events.

---

## Why Latency Matters In HFT Systems

Lower latency can improve:

- probability of reaching the exchange before market moves
- queue position for limit orders
- ability to cancel stale orders
- speed of risk updates after fills
- freshness of market data consumed by strategies

The backend interview framing should avoid vague "faster is better" answers. Explain where latency appears and how you measure it.

---

## Backend/System Relevance

Common latency sources:

- Network: physical distance, routing, packet loss, TLS handshakes, DNS, TCP slow start.
- Serialization: JSON parsing, object allocation, schema validation, compression.
- API layer: middleware, auth, logging, rate limiting, sync dependencies.
- Queues: broker publish latency, consumer lag, partition hot spots.
- Database: locks, index misses, connection pool waits, fsync, slow queries.
- Application code: blocking calls, global locks, slow algorithms, excessive allocations.
- Runtime: Python GIL contention, GC pauses, thread scheduling, event loop blockage.
- Exchange: venue throttling, matching engine load, gateway delays.

Backend latency budget example:

```text
order API receive -> validation:       200 us
risk cache lookup:                     100 us
persist order intent:                  800 us
publish to connector:                  300 us
connector encode + send:               150 us
network to exchange:                 1-5 ms
exchange ack return:                 1-5 ms
event processing + websocket update:   500 us
```

Exact numbers vary by system, but the interview point is to decompose the path.
This output also shows why "optimize Python code" is not always the first answer: network and exchange time may dominate the total path.

---

## Practical Optimization Examples

Hot path design:

- Keep hot path short and predictable.
- Cache read-heavy reference data such as symbols, account flags, and risk limits.
- Pre-create exchange sessions instead of authenticating per order.
- Avoid blocking database calls for every market data update.
- Use binary protocols or compact messages where JSON overhead is too high.
- Batch non-critical writes, but not at the cost of losing auditability.
- Separate fast in-memory state from durable audit logs.
- Keep logging structured but avoid synchronous log writes in the hot path.

Python example: avoid blocking the event loop:

```python
import asyncio

async def handle_market_data(message: bytes) -> None:
    update = decode_message(message)
    update_in_memory_book(update)
    await publish_update(update)

async def bad_handler(message: bytes) -> None:
    update = decode_message(message)
    write_to_database_sync(update)  # blocks every other coroutine
    await publish_update(update)
```

Behavior: if `write_to_database_sync()` takes 50 ms, every other coroutine sharing that event loop can be delayed by the same blocking call.

Better pattern:

```python
async def handle_market_data(message: bytes, audit_queue: asyncio.Queue) -> None:
    update = decode_message(message)
    update_in_memory_book(update)
    audit_queue.put_nowait(update)
    await publish_update(update)
```

This version updates the in-memory book and publishes quickly, while audit persistence can be handled by a separate worker. The justification is not "ignore durability"; it is "do not put slow disk/database work on the hottest message path unless the design explicitly requires it."

---

## Network Latency

Network latency includes:

- client to backend
- backend to exchange
- exchange to backend
- backend to downstream consumers

Production considerations:

- Keep exchange connectors close to exchange endpoints when possible.
- Reuse TCP/TLS sessions.
- Avoid per-request DNS lookups.
- Monitor packet loss and retransmits.
- Use heartbeats to detect dead connections quickly.
- Understand cloud networking variability if not colocated.

Keep in mind: latency is not only code speed. Network distance, routing, deployment topology, and exchange behavior can be larger factors.

---

## Serialization And API Latency

JSON is convenient but can be expensive at high message rates.

Costs:

- parse time
- object allocation
- validation overhead
- larger payload size
- garbage collection pressure

Tradeoffs:

- JSON: easy debugging, broad compatibility, slower/larger.
- Protobuf/FlatBuffers/SBE: compact and faster, more operational complexity.
- FIX: common exchange protocol, text-based tag-value format, operationally standardized.

Backend answer:

Use simple formats for control-plane APIs. Use compact, schema-driven formats for high-throughput data-plane paths if profiling shows serialization is a bottleneck.

---

## Database Latency

Databases are usually not in the ultra-low-latency path for market data or order routing unless the system design specifically budgets for it.

Use DB for:

- audit trail
- order history
- reconciliation
- configuration
- reporting

Avoid DB in hot path when:

- each order requires multiple synchronous reads
- market data updates are written one row at a time
- queries are missing indexes
- connection pools saturate under bursts

Production compromise:

```text
hot path:
  validate from cache -> submit -> append event

background path:
  consume events -> persist normalized history -> reconcile/report
```

This output separates the urgent path from the durable/reporting path. The hot path answers "can we react now?", while the background path answers "can we audit and reconcile later?"

---

## Monitoring Latency

Measure latency at boundaries:

- API ingress timestamp
- validation completed
- risk completed
- connector enqueue
- exchange send timestamp
- exchange ack received
- event persisted
- websocket delivered

Use:

- histograms, not only averages
- p50/p95/p99 dashboards
- trace IDs and `client_order_id`
- queue depth and consumer lag
- event loop lag
- GC pause metrics
- socket reconnect counts
- stale market data age

Alert on:

- p99 submit-to-ack above threshold
- growing connector queue
- missing heartbeats
- stale data feed
- high retry rate
- orders stuck in pending states

---

## Production Debugging Scenarios

Scenario: p99 order latency spikes but CPU is normal.

Investigate:

- connection pool wait time
- downstream service latency
- queue lag
- packet loss/retransmits
- lock contention
- synchronous logging
- DNS/TLS renegotiation
- GC pauses

Scenario: websocket updates are delayed.

Investigate:

- event consumer lag
- slow subscribers causing backpressure
- large messages
- serialization time
- event loop blockage
- network congestion

Scenario: market data handler falls behind during open.

Investigate:

- per-message database writes
- expensive JSON decoding
- slow downstream fanout
- single-threaded hot loop
- unbounded queue growth

---

## Common Interview Questions

- How would you measure order latency end-to-end?
  - Answer: Add timestamps at API ingress, validation, risk, enqueue, connector send, exchange ack/fill, event processing, and client delivery.
- What is tail latency and why does it matter?
  - Answer: Tail latency is high-percentile latency; it matters because a small number of slow orders can create real trading loss or stale decisions.
- Where can latency hide in a Python backend?
  - Answer: Network hops, TLS, serialization, logging, DB calls, locks, queue wait, event-loop blocking, GC, and exchange response time.
- Why can adding a queue improve reliability but hurt latency?
  - Answer: Queues absorb bursts and isolate failures, but each queued item waits behind earlier work and can hide backlogs.
- When would you choose JSON vs binary encoding?
  - Answer: Use JSON for low/medium-rate APIs and debuggability; use binary/compact schemas when message rate, size, or encoding cost is a proven bottleneck.
- How do you debug latency spikes in production?
  - Answer: Separate p50/p99, then check deploys, traffic, queue depth, dependency latency, CPU/GC, logs, traces, and exchange status.

Keep in mind:

Measure first and report p99, not only averages. Be careful with network/exchange latency, synchronous DB writes, unbounded queues, and retries without deadlines.

---

## Quick Revision

- Latency is end-to-end, not only function runtime.
- Tail latency matters in trading.
- Network, serialization, queues, DB, locks, GC, and event-loop blockage are common bottlenecks.
- Measure every boundary with histograms.
- Keep hot paths short, cached, asynchronous where appropriate, and observable.
