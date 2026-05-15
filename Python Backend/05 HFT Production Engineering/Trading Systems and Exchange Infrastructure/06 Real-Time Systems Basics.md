# Real-Time Systems Basics

Tags: #real-time #event-driven #queues #streaming #backend #reliability #interview

Interview lens: real-time trading systems are event-driven backend systems where freshness, ordering, backpressure, and recovery matter as much as throughput.

---

## Concept

A real-time system processes events as they happen and makes updated state available quickly.

Trading examples:

- market data tick updates an order book
- execution report updates order state
- fill updates position and risk
- stale feed alert triggers kill switch
- cancel request reaches exchange before order fills

Real-time does not always mean hard real-time. Most backend trading systems are soft real-time: late responses reduce value or increase risk, but do not usually violate a formal timing guarantee.

---

## Why It Matters In Trading Systems

Trading infrastructure depends on fresh state:

- stale market data can trigger bad orders
- delayed fills can make positions wrong
- lagging risk updates can allow excessive exposure
- slow cancels can leave unwanted live orders
- delayed alerts can hide exchange outages

Backend interviews focus on how you design event flow, not on predicting prices.

---

## Backend/System Relevance

Core building blocks:

- event producers: exchange connectors, APIs, risk engines, schedulers
- event bus: Kafka, NATS, Redis Streams, RabbitMQ, internal queues
- consumers: order state updater, position service, websocket gateway, audit writer
- state stores: in-memory cache, database, event log, snapshot store
- monitors: lag, stale data, processing latency, queue depth, error rate

Architecture:

```text
exchange connector
  -> normalized event stream
  -> order state consumer
  -> position/risk consumer
  -> websocket gateway
  -> audit/history writer
```

This output shows one event feeding multiple consumers. That is the main benefit of event-driven design: order state, risk, client updates, and audit history can each be handled by the service that owns that responsibility.

---

## Event-Driven Systems

Event-driven systems model changes as events:

- `OrderSubmitted`
- `OrderAcked`
- `OrderRejected`
- `OrderPartiallyFilled`
- `OrderFilled`
- `CancelRequested`
- `CancelRejected`
- `MarketDataBookUpdated`

Benefits:

- decouples producers and consumers
- supports replay
- improves auditability
- enables multiple downstream views

Risks:

- duplicate events
- out-of-order events
- poison messages
- consumer lag
- schema evolution issues
- unclear ownership of state

Production rule: every event consumer should be idempotent or have a clear deduplication strategy.

---

## Asynchronous Processing

Async processing helps avoid blocking on I/O:

- websocket receive loops
- REST calls to exchange
- event bus consumers
- timers and heartbeats
- fanout to clients

Python example:

```python
import asyncio

async def consume_events(queue: asyncio.Queue) -> None:
    while True:
        event = await queue.get()
        try:
            await apply_event(event)
        finally:
            queue.task_done()
```

Example behavior:

```text
queue receives OrderFilled
consumer calls apply_event(OrderFilled)
queue marks the item done after processing
```

The `finally` block matters because the queue should not think work is still running forever if `apply_event()` raises. Production code would also add error handling, retries, and a dead-letter path.

Backend tradeoff:

- Async improves I/O concurrency.
- It does not make CPU-heavy code faster.
- Blocking functions inside async handlers can freeze the event loop.

---

## Queues And Workers

Queues absorb bursts and decouple services.

Useful for:

- audit writes
- notifications
- reconciliation jobs
- non-critical enrichment
- slow downstream integrations

Dangerous for:

- latency-sensitive order submit path if queueing delay is uncontrolled
- cancellation path if lower priority than normal orders
- market data if consumers cannot keep up

Queue design considerations:

- bounded vs unbounded queues
- priority for cancels/risk events
- dead-letter queues
- retry deadlines
- partitioning by order/account/symbol
- preserving per-order ordering
- monitoring consumer lag

---

## Concurrency Relevance

Concurrency problems in trading backends:

- two fills update same position concurrently
- cancel and fill race
- duplicate events processed by multiple workers
- order state transitions race
- shared in-memory order book updated without protection
- websocket send loop blocked by slow client

Safe patterns:

- single writer per order or account partition
- compare-and-swap/versioned state updates
- idempotency keys
- event sequence numbers
- partitioned consumers
- immutable event payloads
- explicit state transition validation

---

## Throughput Vs Latency

Throughput is how many events per second the system can process.

Latency is how long a single event takes to move through the system.

Tradeoffs:

- batching improves throughput but can add latency
- compression reduces bandwidth but costs CPU
- durable writes improve recovery but add I/O latency
- queues absorb bursts but add waiting time
- more workers increase throughput but can break ordering

Interview answer: explain the workload and which metric matters most for that path.

Example:

- order cancels: prioritize latency and reliability
- end-of-day reports: prioritize throughput
- market data display: prioritize freshness and drop stale updates if needed
- audit log: prioritize durability and completeness

---

## Fault Tolerance

Failure modes:

- producer crash
- consumer crash
- broker outage
- duplicate delivery
- message schema mismatch
- slow consumer
- disk full on audit store
- network partition
- exchange disconnect

Resilience patterns:

- durable event log
- replay from offsets
- idempotent consumers
- dead-letter queues
- circuit breakers
- backpressure
- degraded mode
- reconciliation jobs
- health checks that include business freshness

Business health checks:

- last market data update age
- last execution report age
- open orders count by venue
- stuck pending orders
- unmatched fills
- connector sequence gaps

---

## Monitoring Real-Time Systems

Metrics:

- event processing latency
- queue depth
- consumer lag
- event rate by type
- dropped messages
- retry count
- dead-letter count
- websocket connections
- slow clients
- stale feed age
- order state transition errors

Logs should include:

- `request_id`
- `client_order_id`
- `order_id`
- `exchange_order_id`
- venue
- sequence number
- state transition
- latency timings

Traces should show:

```text
API request
  -> validation
  -> risk
  -> event publish
  -> connector send
  -> exchange ack
  -> event consumer
  -> websocket delivery
```

This output is what a trace should make visible. If users see stale data, the trace helps locate whether the delay came from validation, queueing, exchange ack, consumer lag, or websocket delivery.

---

## Production Debugging Examples

Scenario: consumer lag increases after market open.

Investigate:

- event rate change
- slow database writes
- partition imbalance
- poison messages causing retries
- downstream timeout
- CPU saturation
- object allocation/GC

Scenario: positions are wrong after duplicate fills.

Investigate:

- event IDs and exchange execution IDs
- idempotency of position consumer
- replay behavior after restart
- whether fill was applied twice
- transaction boundaries in state store

Scenario: market data book is inconsistent.

Investigate:

- sequence gaps
- missed snapshot
- out-of-order deltas
- reconnect without replay
- concurrent writes to shared book

---

## Common Interview Questions

- What is event-driven architecture and why is it useful for trading systems?
  - Answer: It moves state changes as events between producers and consumers; it fits trading because order, fill, market data, and risk updates are time-sensitive streams.
- How do you handle duplicate or out-of-order events?
  - Answer: Use event IDs, sequence numbers, per-order/symbol ordering, idempotent consumers, and replay-safe state updates.
- How do queues affect latency?
  - Answer: Queues decouple producers from consumers and absorb bursts, but add wait time, lag, and retry/idempotency complexity.
- How would you design a real-time order update pipeline?
  - Answer: Persist order events, publish them to a bus, consume in ordered partitions, update materialized state, and fan out to websocket clients with replay/resync support.
- What do you monitor in a streaming backend?
  - Answer: Monitor lag, oldest message age, processing rate, drop count, queue depth, event age, stale order states, consumer errors, and downstream send latency.
- How do you protect the system from slow consumers?
  - Answer: Use bounded queues, per-consumer isolation, backpressure, slow-consumer disconnects, and replay instead of infinite buffering.

Keep in mind:

Naming a queue or broker is not enough. Explain ordering, idempotency, bounded queues, consumer lag, and business freshness such as stale market data or stuck orders.

---

## Quick Revision

- Real-time trading systems are event-driven and stateful.
- Freshness, ordering, idempotency, and backpressure are core concerns.
- Queues improve decoupling but can add latency.
- Async helps I/O concurrency but does not fix CPU-bound work.
- Monitor lag, stale data, dropped messages, and stuck order states.
