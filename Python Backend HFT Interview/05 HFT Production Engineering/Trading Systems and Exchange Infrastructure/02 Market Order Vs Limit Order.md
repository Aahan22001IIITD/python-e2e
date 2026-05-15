# Market Order Vs Limit Order

Tags: #orders #market-order #limit-order #liquidity #backend #interview

Interview lens: market and limit orders differ less in API shape and more in execution certainty, price control, risk checks, routing behavior, and latency sensitivity.

---

## Concept

A market order asks to execute immediately at the best available price. It prioritizes speed and execution probability over price certainty.

A limit order specifies a maximum buy price or minimum sell price. It prioritizes price control over immediate execution.

Examples:

- Market buy 100 shares: buy now at available ask prices.
- Limit buy 100 shares at `185.25`: buy only at `185.25` or lower.
- Limit sell 100 shares at `186.10`: sell only at `186.10` or higher.

---

## Why It Matters In Trading Systems

Order type changes backend risk, validation, routing, and user-visible behavior.

Market orders can execute quickly but may fill at worse prices during volatility or low liquidity. Limit orders may rest on the exchange book and remain active for a long time. Backend systems must handle both immediate terminal states and long-lived live orders.

---

## Backend/System Relevance

Market order handling:

- Validate quantity, account, symbol, market status, allowed order type.
- Estimate notional risk using current market data or configured collars.
- Submit quickly; execution may happen immediately.
- Expect fast fills, possible multiple execution reports, or reject.
- Monitor slippage and reject rates.

Limit order handling:

- Validate limit price, tick size, quantity, time-in-force, risk.
- Track live order state after acknowledgement.
- Handle partial fills over time.
- Support cancel/modify flows.
- Reconcile resting orders.

Backend difference:

```text
market order:
  submit -> ack/reject -> fills quickly -> terminal state

limit order:
  submit -> ack -> maybe rest on book -> partial fills/cancel/modify -> terminal state later
```

---

## Liquidity And Exchange Behavior

Liquidity means available quantity at prices where the order can execute.

Market order:

- Consumes available liquidity.
- May match across multiple price levels.
- Can have high slippage if book depth is thin.

Limit order:

- Provides liquidity if it rests on the book.
- Consumes liquidity if the limit price crosses the current market.
- May never execute if the market does not reach the limit price.

Example:

```text
Order book asks:
185.25 x 50
185.30 x 30
185.40 x 100

Market buy 100:
50 @ 185.25
30 @ 185.30
20 @ 185.40

Limit buy 100 @ 185.30:
50 @ 185.25
30 @ 185.30
20 remains unfilled or rests depending on venue rules
```

---

## Practical Backend Example

API validation shape:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    quantity: int
    limit_price: float | None = None

def validate_order(order: OrderRequest) -> None:
    if order.quantity <= 0:
        raise ValueError("quantity must be positive")

    if order.order_type == "MARKET" and order.limit_price is not None:
        raise ValueError("market order must not include limit_price")

    if order.order_type == "LIMIT" and order.limit_price is None:
        raise ValueError("limit order requires limit_price")

    if order.order_type not in {"MARKET", "LIMIT"}:
        raise ValueError("unsupported order type")
```

Production systems also validate:

- symbol tradability
- session status
- tick size
- min/max order size
- account permissions
- price collars
- time-in-force
- duplicate client order IDs

---

## Latency Implications

Market orders:

- More sensitive to submit latency because the price can move before reaching the exchange.
- Risk checks need to be fast and precomputed where possible.
- Slow serialization or queueing can directly increase slippage.

Limit orders:

- Submit latency still matters for queue position at the exchange.
- Earlier arrival at the same price may get better execution priority.
- Modify/cancel latency matters when reacting to market changes.

Monitoring:

- order submit-to-ack latency by order type
- market order slippage
- limit order fill ratio
- cancel latency
- reject rate for price collars/tick size
- queue delay before connector send

---

## Reliability Considerations

- Market orders need strong duplicate protection; duplicate submissions can create unwanted positions.
- Limit orders need accurate live-order tracking and cancel handling.
- Reconnect logic must resync open orders.
- Risk reservations must release correctly after cancel/reject/fill.
- Client-visible status must distinguish `accepted`, `filled`, `partially_filled`, and `cancel_pending`.

Production issue:

```text
Client retries market order after timeout.
Backend lacks idempotency.
Exchange receives two market orders.
Position doubles before monitoring detects it.
```

Fix:

- Require `client_order_id`.
- Store request before submit.
- Return existing order on retry.
- Reconcile by client/exchange order IDs.

---

## Interview Scenarios

Question: Why can a market order execute at multiple prices?

Answer: it consumes available liquidity across book levels until quantity is filled or no liquidity remains.

Question: Why can a limit order execute immediately?

Answer: if its price crosses available liquidity, it acts like an aggressive order up to the limit price.

Question: Why does latency matter for limit orders?

Answer: arrival time affects queue priority and cancel/replace responsiveness.

Question: How should backend handle a retry of a market order?

Answer: use idempotency, never blindly create a second exchange order after a timeout.

---

## Common Engineering Mistakes

- Assuming market orders always fill completely.
- Assuming limit orders always rest.
- Not validating tick size or price bounds.
- Treating API acceptance as execution success.
- Ignoring partial fills.
- Letting client retries create duplicate market orders.
- Forgetting to release reserved risk on reject/cancel.

---

## Quick Revision

- Market order prioritizes execution speed.
- Limit order prioritizes price control.
- Market orders can have slippage.
- Limit orders can rest, partially fill, or execute immediately if crossing.
- Backend handling differs in risk, state duration, retries, and reconciliation.
- Latency affects market slippage and limit order queue position.
