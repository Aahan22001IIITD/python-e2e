# Trading Systems And Exchange Infrastructure

Tags: #trading-systems #exchange-connectivity #backend #hft #low-latency #interview

Interview lens: explain trading infrastructure as production backend systems: state machines, APIs, streams, retries, idempotency, latency budgets, observability, and failure recovery.

---

## How To Use These Notes

Read in this order for quick interview preparation:

1. [[01 Order Lifecycle Basics]]
2. [[02 Market Order Vs Limit Order]]
3. [[03 Latency Importance In Trading Systems]]
4. [[04 Exchange Connectivity Basics]]
5. [[05 WebSocket Vs REST APIs]]
6. [[06 Real-Time Systems Basics]]
7. [[07 Interview Revision And Production Scenarios]]

---

## Backend Mental Model

A trading platform is usually split into:

- Control plane: REST APIs, dashboards, admin tools, configuration, account setup, risk limits.
- Data plane: market data streams, order routing, execution reports, position updates, risk events.
- Connectivity plane: exchange sessions, FIX/websocket clients, authentication, heartbeats, reconnects.
- State plane: order state machine, execution store, position cache, audit log, reconciliation jobs.
- Observability plane: latency metrics, dropped message alerts, exchange health, queue depth, stale data checks.

Practical architecture:

```text
client / strategy
  -> order API
  -> validation + risk checks
  -> order manager
  -> exchange connector
  -> exchange
  <- acknowledgements / fills / rejects
  <- event stream + order state updates
```

This output is the simplest mental model for the whole section: commands move down toward the exchange, while facts from the exchange move back up as events. Most production bugs happen when one side is treated as synchronous even though the real system is distributed.

Interview answer pattern:

1. Define the trading concept.
2. Describe the backend components involved.
3. Explain state transitions and failure modes.
4. Mention latency, reliability, and observability.
5. Give a practical production example.

---

## Core Interview Themes

- Orders are stateful workflows, not simple database rows.
- Exchange connectivity is long-lived, stateful, and failure-prone.
- Websockets/FIX streams need sequence handling, heartbeats, reconnects, and resync.
- REST is good for commands and snapshots; streams are good for real-time changes.
- Low latency is mostly about removing waits, allocations, blocking I/O, slow serialization, and unnecessary hops.
- Reliability means knowing whether an order was accepted, rejected, filled, cancelled, or unknown.
- Observability must include business health, not only CPU and memory.

---

## Quick Revision

- Know the order state machine.
- Know REST vs websocket tradeoffs.
- Know how reconnect and replay work.
- Know idempotency and duplicate handling.
- Know latency bottlenecks across network, code, serialization, queues, and storage.
- Know what to monitor during a live trading incident.
