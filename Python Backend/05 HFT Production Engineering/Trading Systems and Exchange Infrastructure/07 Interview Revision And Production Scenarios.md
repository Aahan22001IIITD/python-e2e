# Interview Revision And Production Scenarios

Tags: #trading-systems #backend #hft #interview-questions #production #revision

Interview lens: answer like a backend engineer responsible for live trading infrastructure. Focus on state, latency, reliability, observability, and recovery.

---

## Top 25 Trading/Backend Infrastructure Interview Questions

1. Walk me through the lifecycle of an order from API request to exchange execution.
   - Answer: An order usually flows through API validation, auth/risk checks, durable persistence, routing, connector send, exchange ack, execution reports, internal state updates, and client notifications.
2. What is the difference between order acknowledgement and execution?
   - Answer: Acknowledgement means accepted by the API/backend/exchange path; execution means the order traded and produced one or more fills.
3. What happens if an order API request times out after the backend sent the order to the exchange?
   - Answer: Treat timeout after send as `UNKNOWN`; inspect outbound logs and reconcile with exchange state before returning a final answer or retrying.
4. How do you make order submission idempotent?
   - Answer: Require a client order ID/idempotency key, persist it atomically with the order intent, compare payload hashes, and return the original result on replay.
5. How do you handle partial fills?
   - Answer: Model partial fills explicitly; update filled quantity, remaining quantity, average price, and position idempotently per execution ID.
6. Can a cancel request fail? Explain realistic cases.
   - Answer: Yes. A cancel can lose the race with a fill, target an already-final order, hit an exchange reject, or be unconfirmed during connectivity loss.
7. How would you design an order state machine?
   - Answer: Define valid states and transitions such as `NEW`, `PENDING_ACK`, `ACKED`, `PARTIALLY_FILLED`, `FILLED`, `PENDING_CANCEL`, `CANCELLED`, `REJECTED`, and `UNKNOWN`.
8. What is the difference between market and limit orders from a backend perspective?
   - Answer: Market orders prioritize execution and consume liquidity; limit orders constrain price and may rest, partially fill, or execute immediately if crossing.
9. Why does latency matter for market orders and limit orders?
   - Answer: Market-order latency affects slippage; limit-order latency affects queue position, missed fills, and cancel/replace races.
10. How would you measure end-to-end order latency?
    - Answer: Add timestamps at every boundary: API ingress, validation, queue, connector send, exchange ack/fill, event bus, DB update, and websocket delivery.
11. What are common latency bottlenecks in a Python trading backend?
    - Answer: Common bottlenecks include DB writes, connection pools, JSON serialization, logging, locks, queues, event-loop blocking, GC, network, and exchange latency.
12. When would you use REST vs websocket?
    - Answer: Use REST for commands and snapshots; use websocket for continuous updates such as order events and market data.
13. How do you safely reconnect a websocket feed?
    - Answer: Reconnect with backoff/jitter, refresh auth, resubscribe, validate sequence numbers, replay or snapshot missing data, and mark streams stale until recovered.
14. What are sequence numbers used for?
    - Answer: Sequence numbers detect missed, duplicate, or out-of-order messages and tell consumers when resync is required.
15. What is a heartbeat and what should happen when heartbeats stop?
    - Answer: A heartbeat proves the connection/session is alive; missed heartbeats should mark the feed unhealthy and trigger controlled reconnect/recovery.
16. What is FIX used for at a high level?
    - Answer: FIX is a stateful trading protocol for orders, cancels, execution reports, heartbeats, and session-level sequence management.
17. How do you recover after an exchange connector crashes?
    - Answer: On connector crash, reload durable state, inspect outbound commands, reconcile open orders/executions with the exchange, and avoid blind resubmission.
18. How do you detect stale market data?
    - Answer: Detect stale market data with last-message age, heartbeat age, sequence gap metrics, crossed-book checks, and consumer lag.
19. How do queues help and hurt a trading backend?
    - Answer: Queues decouple services and absorb bursts, but increase latency, hide backlog, and require idempotent replay/retry handling.
20. How do you handle duplicate or out-of-order events?
    - Answer: Use event IDs, sequence checks, partitioned ordering, idempotent consumers, and state-machine validation.
21. How would you monitor exchange connectivity?
    - Answer: Monitor session state, heartbeat age, reconnects, sequence gaps, rejects, throttles, stale data age, queue depth, and order round-trip latency.
22. What should be logged for an order-related production incident?
    - Answer: Log request ID, client order ID, exchange order ID, state transition, venue, symbol, quantities, latency, error/reject code, and sanitized raw exchange reference.
23. How would you prevent slow websocket clients from affecting the system?
    - Answer: Use per-client bounded queues, backpressure, disconnect slow consumers, isolate fanout paths, and provide replay/resync instead of infinite buffering.
24. What is reconciliation and why is it necessary?
    - Answer: Reconciliation compares internal state with exchange/account truth so unknown, missed, or duplicated events become visible and repairable.
25. How would you design a backend service used by multiple trading strategies?
    - Answer: Expose stable APIs, enforce auth/risk/idempotency, isolate strategies by account/limits, provide real-time updates, and centralize audit, monitoring, and kill switches.

---

## Most Important Concepts To Revise Before Interview

- Order lifecycle: creation, validation, routing, ack, fill, cancel, reject, unknown.
- Order state machine: valid transitions and race conditions.
- Idempotency: client order IDs, retries, duplicate detection.
- Exchange connectivity: sessions, auth, heartbeats, reconnect, resubscribe, replay.
- FIX basics: logon, heartbeat, sequence numbers, execution reports.
- Websocket basics: persistent stream, heartbeats, backpressure, sequence gaps.
- REST basics: commands, snapshots, idempotent retries, status semantics.
- Latency: p50/p95/p99, network, queues, serialization, DB, event loop, GC.
- Event-driven architecture: producers, event bus, consumers, replay, dedupe.
- Reliability: reconciliation, audit logs, durable state, kill switches, stale data detection.

---

## Common Backend Failures In Trading Systems

Duplicate order submission:

- Cause: client retries after timeout and backend lacks idempotency.
- Fix: require `client_order_id`, persist before submit, return existing order on retry.

Order stuck in pending state:

- Cause: lost execution report, connector crash, consumer lag, sequence gap.
- Fix: alert on stale pending states, reconcile open orders with exchange.

Wrong position:

- Cause: duplicate fill application, missing fill, out-of-order events, replay bug.
- Fix: dedupe by execution ID, replay event log, compare with exchange/account snapshot.

Stale market data:

- Cause: websocket disconnect, heartbeat not monitored, consumer lag.
- Fix: track last update age, mark feed unhealthy, resync from snapshot.

Cancel accepted by API but order fills:

- Cause: API accepted command, exchange had not cancelled yet.
- Fix: expose `PENDING_CANCEL`, process fill as authoritative, explain cancel race.

Connector overload:

- Cause: burst of orders/cancels, rate limits, slow exchange responses.
- Fix: throttle by venue, prioritize risk/cancel messages, monitor queue depth.

Websocket fanout lag:

- Cause: slow clients, large messages, blocked event loop, unbounded queues.
- Fix: per-client bounded queues, disconnect slow clients, optimize serialization.

---

## Common Exchange Connectivity Problems And Fixes

Authentication failures:

- Check API key permissions, IP allowlist, clock drift, token expiry, signature payload.
- Fix with key rotation process, clock sync, safe token refresh, secret redaction.

Dropped websocket connection:

- Check heartbeat age, load balancer idle timeout, network events, exchange status.
- Fix with heartbeat monitor, reconnect backoff, resubscribe, snapshot/replay.

Sequence gaps:

- Check expected vs received sequence number.
- Fix by marking stream stale, fetching snapshot, replaying deltas, or reconnecting.

Exchange rate limits:

- Check reject codes and request rate by endpoint/session.
- Fix with throttling, batching where safe, cancel priority, retry deadlines.

Unknown order status:

- Check outbound log, exchange order query, open order snapshot, execution reports.
- Fix with reconciliation and explicit `UNKNOWN` state until confirmed.

Message format rejects:

- Check tick size, price precision, required tags/fields, time-in-force, symbol format.
- Fix with venue-specific validation before submit.

Session logon failure:

- Check credentials, sequence number reset rules, heartbeat interval, environment endpoint.
- Fix with controlled session reset and operator-visible runbook.

---

## Real-World Production Debugging Scenarios

### Scenario 1: p99 Order Latency Spikes

Symptoms:

- API p50 normal, p99 high.
- Traders report late acks.
- Connector queue depth grows.

Debug path:

- Break down latency by API, risk, queue, connector, network, exchange ack.
- Check connection pool waits, event loop lag, GC pauses, queue depth, exchange health.
- Compare with market open/close traffic pattern.

Likely fixes:

- reduce synchronous database work
- move non-critical work off hot path
- add bounded queues and backpressure
- optimize serialization
- scale connector partitions safely

### Scenario 2: Missing Websocket Order Update

Symptoms:

- REST shows order filled.
- Client websocket still shows `ACKED`.

Debug path:

- Check event bus offset and consumer lag.
- Check websocket gateway logs by `order_id`.
- Check client reconnect history and last sequence.
- Check slow-client queue drops.

Likely fixes:

- add sequence numbers
- support replay or REST resync
- disconnect slow clients
- expose stale subscription metrics

### Scenario 3: Market Data Book Corruption

Symptoms:

- Best bid/ask invalid.
- Strategy receives impossible spread.

Debug path:

- Check sequence gaps.
- Verify snapshot + delta application.
- Check out-of-order processing.
- Inspect reconnect event.

Likely fixes:

- mark book stale on sequence gap
- rebuild from snapshot
- process deltas through a single writer per symbol
- alert on crossed/invalid book states

### Scenario 4: Duplicate Fill Applied

Symptoms:

- Position is doubled.
- Execution report appears twice after replay.

Debug path:

- Compare exchange execution IDs.
- Inspect consumer idempotency.
- Check replay offset and transaction boundary.

Likely fixes:

- dedupe fills by venue + execution ID
- make position updates idempotent
- commit offset after durable state update

### Scenario 5: Connector Crash During Submit

Symptoms:

- Order API accepted order.
- No final status.
- Connector restarted.

Debug path:

- Inspect outbound message log.
- Query exchange open orders and executions.
- Reconcile by client/exchange order IDs.

Likely fixes:

- keep explicit `UNKNOWN` state
- persist outbound commands
- reconcile on startup
- avoid blind resubmission

---

## Quick Websocket/Backend Revision

Websocket checklist:

- persistent connection, not request-response
- heartbeat/ping-pong
- reconnect with jittered backoff
- authenticate and resubscribe after reconnect
- use sequence numbers
- recover with replay or REST snapshot
- handle duplicates
- bounded per-client queues
- disconnect slow clients
- expose connection, lag, and stale-feed metrics

REST checklist:

- clear resource-oriented endpoints
- request IDs and idempotency keys
- deadlines/timeouts
- safe retry semantics
- pagination for lists
- explicit status responses
- structured errors
- audit logs

---

## Reliability Considerations In Trading Systems

Reliability means:

- every order has an auditable history
- every fill is applied exactly once logically
- unknown states are detected and reconciled
- stale feeds are visible and acted on
- retries do not create duplicate business actions
- services degrade safely under exchange or network failure

Practical controls:

- idempotency keys for write APIs
- durable event/outbound logs
- sequence checks
- reconciliation jobs
- explicit state machines
- kill switches
- circuit breakers
- bounded retries with deadlines
- stale data alerts
- runbooks for connector/session issues

Good production answer:

```text
I would not assume failure or success after a timeout.
I would persist the intent, track the outbound message, expose UNKNOWN,
then reconcile with exchange open orders/executions before retrying.
```

---

## Low-Latency Backend Engineering Tips

- Measure before optimizing; use p95/p99 histograms.
- Decompose latency by service boundary.
- Keep hot paths short and predictable.
- Cache stable reference data.
- Avoid blocking I/O in event loops.
- Avoid synchronous logging in hot paths.
- Reuse connections and authenticated sessions.
- Prefer compact schemas for high-rate streams when JSON is a bottleneck.
- Avoid unbounded queues.
- Partition by order/account/symbol to preserve local ordering.
- Prioritize cancels and risk events.
- Reduce allocations in high-frequency handlers.
- Keep database writes off the market data hot path when possible.
- Monitor event loop lag, GC pauses, queue depth, and stale data age.

Interview trap: never claim Python is impossible for trading systems. A good answer is that Python is often used for orchestration, APIs, automation, tools, and some event processing, while extremely latency-critical paths may use C++/Java/Rust or exchange-native systems.

---

## Backend Architecture Patterns Commonly Used In Trading Infrastructure

Order manager:

- Owns order state machine.
- Applies execution reports.
- Emits order updates.

Exchange connector:

- Owns venue protocol/session.
- Handles auth, heartbeats, reconnects, rate limits.
- Normalizes venue events.

Event bus:

- Decouples exchange events from downstream consumers.
- Supports replay and fanout.

Risk service:

- Validates orders before routing.
- Tracks limits, exposure, kill switches.

Market data service:

- Maintains snapshots/order books.
- Publishes normalized real-time updates.

Websocket gateway:

- Delivers real-time updates to clients.
- Handles subscriptions, backpressure, reconnect semantics.

Reconciliation worker:

- Compares internal order/position state with exchange/account truth.
- Repairs or alerts on mismatches.

Audit/event store:

- Stores immutable order, execution, and connector events.
- Supports debugging, compliance, and replay.

Circuit breaker/kill switch:

- Stops routing under unsafe conditions: stale data, exchange outage, risk breach, abnormal reject rate.

---

## Final One-Minute Revision

- Orders are distributed state machines.
- Ack is not fill.
- Cancel is not guaranteed.
- Timeout after send means unknown.
- REST is command/snapshot; websocket is stream/update.
- Reconnect requires resubscribe and resync.
- Sequence numbers detect loss and ordering issues.
- Queues decouple but add latency.
- Idempotency prevents duplicate business actions.
- Reconciliation turns uncertainty into known state.
