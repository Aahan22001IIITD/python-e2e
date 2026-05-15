# Order Lifecycle Basics

Tags: #orders #execution #backend #state-machine #hft #interview

Interview lens: an order lifecycle is a distributed state machine across client, backend services, exchange connector, and exchange.

---

## Concept

An order lifecycle is the path from intent to final state:

1. Order creation
2. Validation
3. Risk checks
4. Routing
5. Exchange submission
6. Acknowledgement
7. Matching / execution
8. Fill reporting
9. Cancellation or modification
10. Final reconciliation

Important states:

- `NEW`: created internally, not yet accepted by exchange.
- `VALIDATED`: passed local schema, account, symbol, and risk checks.
- `PENDING_SUBMIT`: sent to connector, awaiting exchange response.
- `ACKED`: accepted by exchange.
- `PARTIALLY_FILLED`: some quantity executed.
- `FILLED`: entire quantity executed.
- `PENDING_CANCEL`: cancel requested, awaiting exchange response.
- `CANCELLED`: remaining quantity cancelled.
- `REJECTED`: rejected locally or by exchange.
- `UNKNOWN`: backend lost certainty and must reconcile.

---

## Why It Matters In Trading Systems

Orders are real money workflows. A backend cannot treat `POST /orders` as "insert row and return success". It must know whether the order reached the exchange, whether it was accepted, whether it filled, and whether client-visible state is consistent with exchange state.

The dangerous state is not failure; it is uncertainty. If the service times out after sending an order, the order may still be live at the exchange.

---

## Backend/System Relevance

Backend services usually involved:

- API gateway: authentication, rate limits, request IDs.
- Order API: command validation and idempotency.
- Risk service: account limits, max order size, symbol restrictions.
- Order manager: durable state machine and event emission.
- Exchange router: chooses venue/session.
- Exchange connector: translates internal order to venue protocol.
- Execution consumer: applies acknowledgements, fills, rejects, cancels.
- Reconciliation worker: compares internal state with exchange truth.
- Notification stream: sends updates to strategies, UIs, and downstream services.

Architecture pattern:

```text
POST /orders
  -> validate request
  -> reserve risk / buying power
  -> persist order intent
  -> publish submit command
  -> connector sends to exchange
  -> exchange sends ack/reject/fill
  -> event consumer updates order state
  -> websocket publishes order update
```

This output shows why order handling is not a single API call. The API accepts intent, the connector talks to the exchange, and later exchange events become the source of truth for user-visible status.

---

## Practical Workflow Example

Client submits a limit buy:

```json
{
  "client_order_id": "cli-20260514-001",
  "symbol": "AAPL",
  "side": "BUY",
  "type": "LIMIT",
  "quantity": 100,
  "limit_price": 185.25
}
```

This request is valid because a limit order includes both quantity and a limit price. The `client_order_id` is important because retries can be matched to the same original intent instead of creating another order.

Backend flow:

1. Validate required fields and supported order type.
2. Check account is allowed to trade `AAPL`.
3. Check risk: max quantity, max notional, kill switch, market status.
4. Persist order with `client_order_id` as idempotency key.
5. Route to configured exchange connector.
6. Submit message to exchange.
7. Apply `ACK`, `PARTIAL_FILL`, `FILL`, `CANCEL_ACK`, or `REJECT`.
8. Publish state updates to websocket clients.

Python-style state transition guard:

```python
ALLOWED_TRANSITIONS = {
    "NEW": {"VALIDATED", "REJECTED"},
    "VALIDATED": {"PENDING_SUBMIT"},
    "PENDING_SUBMIT": {"ACKED", "REJECTED", "UNKNOWN"},
    "ACKED": {"PARTIALLY_FILLED", "FILLED", "PENDING_CANCEL", "REJECTED"},
    "PARTIALLY_FILLED": {"PARTIALLY_FILLED", "FILLED", "PENDING_CANCEL"},
    "PENDING_CANCEL": {"CANCELLED", "FILLED", "PARTIALLY_FILLED", "UNKNOWN"},
}

def transition(current: str, next_state: str) -> str:
    if next_state not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"invalid order transition: {current} -> {next_state}")
    return next_state
```

Example output/behavior:

```text
transition("PENDING_SUBMIT", "ACKED") -> "ACKED"
transition("NEW", "FILLED") -> ValueError
```

The guard prevents impossible shortcuts in the order lifecycle. That matters because fills, rejects, cancels, and unknown states can arrive from different services at different times.

---

## Acknowledgements, Executions, Cancels, And Modifications

Acknowledgement means the exchange accepted the order, not that it executed.

Execution means the order matched against liquidity and generated a fill.

Cancellation means the remaining live quantity was removed from the book. A cancel can fail if the order already filled.

Modification is usually implemented as a replace/amend flow. Some exchanges support native modify; others require cancel and resubmit. Backend systems must preserve lineage between original and replaced orders.

Example edge case:

```text
t0: backend sends cancel
t1: exchange matches remaining quantity
t2: exchange sends fill
t3: exchange sends cancel reject: already filled
```

Correct backend behavior: accept the fill as authoritative and mark the order `FILLED`, not `CANCELLED`.

The output shows the race clearly: the API can accept a cancel command, but the exchange may execute the order before processing that cancel.

---

## Latency And Reliability Considerations

- Validate synchronously only for cheap checks; push expensive checks out of the hot path when safe.
- Avoid database reads per order if limits/config can be cached safely.
- Persist order intent before external submission when auditability matters.
- Use idempotency keys to survive client retries.
- Track exchange sequence numbers to detect gaps.
- Treat timeout after send as `UNKNOWN`, not `REJECTED`.
- Separate command latency from execution latency in metrics.

Useful metrics:

- order API p50/p95/p99 latency
- submit-to-ack latency
- ack-to-fill latency
- cancel request-to-cancel ack latency
- reject rate by reason
- orders in `UNKNOWN`
- stale pending orders
- connector queue depth

---

## Production Debugging Scenarios

Scenario: client says order disappeared.

Check:

- API logs by `client_order_id`.
- Order state history.
- Connector outbound message log.
- Exchange execution reports.
- Websocket delivery logs.
- Reconciliation output.

Likely causes:

- API returned before durable persistence.
- Event consumer lagged behind exchange reports.
- Websocket client missed an update after reconnect.
- Duplicate client order ID was rejected as idempotent replay.
- Order entered `UNKNOWN` after connector timeout.

Scenario: cancel request succeeded in API but order still filled.

Explanation: API accepted the cancel command; it did not guarantee exchange cancellation. The exchange may fill before processing cancel.

---

## Common Interview Questions

- What happens if `POST /orders` times out after the backend sent the order?
  - Answer: Treat the order as `UNKNOWN`; check durable outbound logs and reconcile with the exchange before retrying.
- Difference between order acknowledgement and execution?
  - Answer: Acknowledgement means the order was accepted into a system path; execution means it traded and produced fills.
- Why is idempotency important for order APIs?
  - Answer: It prevents client retries from creating duplicate exchange orders.
- How do you handle duplicate fills?
  - Answer: Dedupe by venue/execution ID and apply fills inside an atomic state update.
- Can a cancel request fail? Why?
  - Answer: Yes. The order may already be filled, rejected, expired, or the exchange may not confirm the cancel.
- Should order status be derived from database state or event history?
  - Answer: Prefer event history as the audit source, with a materialized current-state table for fast reads.
- What if fills arrive before acknowledgements?
  - Answer: Accept the authoritative fill event and let the state machine handle out-of-order transitions.
- Why is `UNKNOWN` a valid production state?
  - Answer: Timeout, crash, or network loss can leave success or failure unconfirmed.

Keep in mind:

Do not equate timeout with failure, or cancel request with cancellation. Always preserve state transitions, partial fills, and raw exchange evidence for audit/debugging.

---

## Common Engineering Mistakes

- Treating order updates as last-write-wins without sequence checks.
- Using database auto-increment IDs as external idempotency keys.
- Forgetting that retries can create duplicate submissions.
- Blocking the hot path on slow downstream services.
- Mixing client-visible status with internal connector status.
- Publishing websocket updates before the durable state update succeeds.
- Not reconciling internal order state against exchange state.

---

## Quick Revision

- Order lifecycle is a state machine across multiple services.
- Ack means accepted, not filled.
- Cancels are requests, not guarantees.
- Partial fills and out-of-order events are normal.
- Timeout after send creates uncertainty.
- Idempotency, sequence numbers, audit logs, and reconciliation are mandatory production concerns.
