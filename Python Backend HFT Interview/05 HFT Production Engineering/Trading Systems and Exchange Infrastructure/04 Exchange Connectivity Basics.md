# Exchange Connectivity Basics

Tags: #exchange-connectivity #fix #websocket #reconnect #backend #hft #interview

Interview lens: exchange connectivity is stateful infrastructure. The hard parts are session lifecycle, message ordering, reconnect, replay, authentication, throttling, and knowing what happened during failures.

---

## Concept

Exchange connectivity is the backend layer that communicates with trading venues.

It usually handles:

- order submission
- order cancellation/modification
- execution reports
- market data subscriptions
- authentication
- heartbeats
- reconnects
- sequence numbers
- rate limits
- protocol translation

Common protocols:

- REST: snapshots, account queries, slower command APIs.
- Websocket: streaming market data and user/order updates.
- FIX: common institutional protocol for orders and execution reports.
- Native binary protocols: low-latency exchange-specific protocols.

---

## Why It Matters In Trading Systems

The exchange connector is often the boundary between internal correctness and external uncertainty.

If it mishandles reconnects, duplicates, sequence gaps, or timeout states, the trading platform may show wrong positions, lose fills, double-submit orders, or fail to cancel risk.

---

## Backend/System Relevance

Connector responsibilities:

- Maintain long-lived sessions.
- Translate internal order commands into venue messages.
- Normalize venue responses into internal events.
- Enforce venue-specific rate limits.
- Track sequence numbers and detect gaps.
- Send heartbeats and detect dead connections.
- Persist inbound/outbound raw messages for audit.
- Expose health to monitoring and routing systems.

Architecture:

```text
order manager
  -> connector command queue
  -> exchange session client
  -> exchange gateway
  <- execution reports / rejects / heartbeats
  <- connector normalizes events
  -> order event stream
```

---

## FIX Protocol High-Level Overview

FIX is a tag-value protocol widely used for order routing and execution reporting.

Example shape:

```text
8=FIX.4.4|35=D|49=BUY_SIDE|56=EXCHANGE|11=cli-1|55=AAPL|54=1|38=100|40=2|44=185.25|
```

Important message types:

- `Logon`: establish session.
- `Heartbeat`: keep session alive.
- `TestRequest`: check peer is alive.
- `NewOrderSingle`: submit new order.
- `OrderCancelRequest`: request cancel.
- `ExecutionReport`: ack, reject, fill, cancel, replace.
- `Reject`: session-level or message-level reject.

Key concepts:

- Sequence numbers detect missing or duplicated messages.
- Sessions have logon/logout lifecycle.
- Execution reports drive order state.
- Resend/replay logic may be required after reconnect.

Interview answer: you do not need to recite FIX tags; explain session management, sequencing, heartbeats, and execution reports.

---

## Websocket Connectivity

Websockets are common for:

- market data streams
- private order updates
- account/position updates
- exchange status notifications

Production websocket client responsibilities:

- authenticate once or refresh token before expiry
- subscribe to channels
- send/expect heartbeats
- reconnect with backoff
- resubscribe after reconnect
- detect stale streams
- handle duplicate messages
- recover missed messages from REST snapshot or replay endpoint

Example reconnect flow:

```text
connection drops
  -> mark feed unhealthy
  -> stop trusting live stream
  -> reconnect with bounded backoff
  -> authenticate
  -> resubscribe
  -> fetch latest snapshot/open orders
  -> replay or compare sequence numbers
  -> mark healthy only after state is consistent
```

---

## Authentication

Exchange APIs may use:

- API key + secret signing
- HMAC signatures
- timestamped requests
- OAuth-like tokens
- client certificates
- FIX credentials
- IP allowlists

Backend concerns:

- Keep secrets out of logs.
- Rotate keys safely.
- Synchronize clock for timestamped signatures.
- Cache tokens but refresh before expiry.
- Separate credentials by environment and strategy/account.
- Fail closed if authentication state is uncertain.

Common bug: system clock drift causes exchange to reject signed requests.

---

## Heartbeats And Dropped Connections

Heartbeat purpose:

- prove peer is alive
- detect half-open TCP connections
- trigger reconnect before data goes stale

Implementation pattern:

```python
import time

class HeartbeatMonitor:
    def __init__(self, timeout_seconds: float):
        self.timeout_seconds = timeout_seconds
        self.last_seen = time.monotonic()

    def mark_seen(self) -> None:
        self.last_seen = time.monotonic()

    def is_stale(self) -> bool:
        return time.monotonic() - self.last_seen > self.timeout_seconds
```

Production behavior:

- missed heartbeat should not immediately create duplicate orders
- mark session unhealthy
- stop routing new orders if required
- reconnect and resync
- alert if unhealthy beyond threshold

---

## Fault Tolerance Considerations

Important connector design choices:

- Active/passive connectors avoid duplicate submissions but need failover.
- Active/active requires strict ownership and deduplication.
- Persistent outbound log helps recover uncertain sends.
- Inbound event log supports replay and audit.
- Sequence number storage must survive process restart.
- Kill switches must be available when connector state is degraded.

Unknown-state example:

```text
connector writes outbound order to socket
process crashes before recording exchange ack
after restart, backend cannot assume rejection
must query open orders / executions and reconcile
```

---

## Production Examples

Exchange rate limit:

```text
symptom: sudden order rejects
logs: "too many requests"
fix: throttle connector, prioritize cancels, expose rate-limit metrics
```

Sequence gap:

```text
symptom: market data book becomes inconsistent
logs: expected sequence 1051, got 1057
fix: mark book stale, fetch snapshot, replay deltas from snapshot sequence
```

Token expiry:

```text
symptom: private websocket silently stops updates
logs: auth expired / unauthorized subscription
fix: refresh token before expiry and resubscribe
```

---

## Common Interview Questions And Traps

- How do you reconnect a websocket feed safely?
  - Answer: Use jittered backoff, refresh auth, resubscribe, validate sequence numbers, snapshot/replay, and mark state stale until caught up.
- What is the purpose of heartbeats?
  - Answer: Heartbeats prove the session/event loop is alive and should trigger reconnect or unhealthy state when missed.
- How do sequence numbers help reliability?
  - Answer: They detect gaps, duplicates, and out-of-order messages so consumers know when to resync.
- What is FIX used for?
  - Answer: FIX is a stateful protocol commonly used for order entry and execution reports, with sessions, heartbeats, and sequence numbers.
- What happens if connector crashes after sending an order?
  - Answer: The order outcome is unknown; recover from outbound logs and exchange open-order/execution queries.
- How do you avoid duplicate orders after reconnect?
  - Answer: Use client order IDs, persisted submit intent, idempotent recovery, and no blind resend after reconnect.
- How would you monitor exchange connectivity?
  - Answer: Monitor logon state, heartbeat age, reconnect count, sequence gaps, rejects, throttle events, stale data age, and order round-trip latency.

Traps:

- Reconnecting without resubscribing.
- Marking connection healthy before state resync.
- Ignoring sequence gaps.
- Treating heartbeat success as order-path success.
- Logging API secrets or signed payloads.
- Retrying order submissions without idempotency.

---

## Quick Revision

- Exchange connectors are stateful services.
- FIX means sessions, sequence numbers, heartbeats, and execution reports.
- Websocket clients need reconnect, resubscribe, dedupe, and resync.
- Timeout/crash after send creates uncertainty.
- Monitor heartbeats, sequence gaps, reconnects, throttles, rejects, and stale data age.
