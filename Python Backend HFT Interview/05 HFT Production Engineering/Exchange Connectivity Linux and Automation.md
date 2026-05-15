# Exchange Connectivity, Linux, And Infrastructure Automation

Tags: #hft #backend #exchange-connectivity #linux #automation #reliability #interview

Interview lens: HFT/backend interviews reward practical operational thinking: state machines, timeouts, reconnects, observability, Linux basics, and safe automation.

---

## Exchange Connectivity

### Concept

Exchange connectivity services maintain sessions to venues, send orders/cancels, receive acknowledgements/fills/market data, and reconcile internal state with external state.

### Why It Matters In Backend Systems

The exchange boundary is unreliable, latency-sensitive, stateful, and financially important. A timeout does not mean an order failed; it may have been accepted while the client lost the response.

### Production Relevance

- Maintain explicit connection/session state.
- Use client order IDs for dedupe and reconciliation.
- Separate "sent", "acknowledged", "rejected", "filled", and "cancel requested".
- Persist state transitions before external side effects when possible.
- Reconcile periodically against exchange truth.

### Practical State Model

```text
NEW -> VALIDATED -> SENT -> ACKED -> PARTIALLY_FILLED -> FILLED
                         \-> REJECTED
                         \-> CANCEL_REQUESTED -> CANCELLED
```

### Backend Example

```python
async def send_order(order: Order) -> None:
    await db.mark_sent(order.id, client_order_id=order.client_order_id)
    try:
        ack = await exchange.send_new_order(order, timeout=0.2)
    except TimeoutError:
        await db.mark_unknown(order.id, reason="exchange_timeout")
        await reconciliation_queue.enqueue(order.client_order_id)
        return

    await db.apply_exchange_ack(
        order_id=order.id,
        exchange_order_id=ack.exchange_order_id,
        status=ack.status,
    )
```

### Interview Traps

- Treating timeout as rejection.
- Not persisting client order ID.
- No reconnect/replay/resync plan.
- Assuming messages arrive exactly once and in order.

### Performance Considerations

- Avoid allocations and blocking calls in hot paths.
- Keep serialization/deserialization efficient.
- Separate critical order paths from slow admin/reporting paths.
- Measure p50, p95, p99, and max latency.

### Scalability And Reliability

- Use one writer per venue/session where ordering matters.
- Add heartbeat monitoring and reconnect backoff.
- Persist sequence numbers for replay/recovery.
- Design degraded mode: stop sending new orders if risk/exchange state is unknown.

### Common Mistakes

- No sequence gap detection.
- Logs do not include `client_order_id` and venue.
- Cancels treated as guaranteed success.
- Reconciliation is manual-only.

### Quick Revision

- Exchange systems are state machines under partial failure.
- Timeout means unknown, not failed.
- Client order IDs, sequence numbers, reconciliation, and heartbeats are core.

---

## Real-Time And Performance-Sensitive Services

### Concept

Real-time backend services optimize predictable latency and timely processing, not just average throughput.

### Why It Matters In Backend Systems

Trading, risk checks, price updates, alerts, and operational dashboards become unsafe or useless when stale or delayed.

### Production Relevance

- Use bounded queues to prevent unbounded memory growth.
- Separate hot paths from expensive enrichment/reporting.
- Prefer monotonic clocks for intervals/timeouts.
- Track event age, not just processing speed.

### Python Example

```python
import time
from collections import deque

class PriceWindow:
    def __init__(self, size: int):
        self.values: deque[float] = deque(maxlen=size)
        self.total = 0.0

    def add(self, price: float) -> float:
        if len(self.values) == self.values.maxlen:
            self.total -= self.values[0]
        self.values.append(price)
        self.total += price
        return self.total / len(self.values)

started = time.monotonic()
```

### Interview Traps

- Optimizing mean latency while p99 is bad.
- Ignoring GC, serialization, logging, and allocations.
- Claiming Python is always too slow instead of isolating hot paths.

### Performance Considerations

- Use profiling and benchmarking before optimizing.
- Avoid deep copies and huge JSON roundtrips in hot paths.
- Batch non-critical work.
- Consider native extensions, separate services, or compiled components for true low-latency paths.

### Scalability And Reliability

- Backpressure is safer than unlimited buffering.
- Dropping stale market data can be valid; dropping order events usually is not.
- Monitor lag and event age.

### Common Mistakes

- Debug-level logs on hot path.
- Unbounded lists/queues.
- Blocking network calls in event loops.

### Quick Revision

- HFT-adjacent Python backends often optimize reliability and bounded latency.
- Know when Python is fine and when a hot path needs another approach.

---

## Linux Production Environments

### Concept

Linux production knowledge means being able to inspect processes, networking, resource use, logs, services, and failures on a running machine/container.

### Why It Matters In Backend Systems

Incidents often require answering: is the process alive, overloaded, stuck on IO, leaking memory, failing DNS, or unable to connect?

### Production Relevance

Useful commands and signals:

| Need | Tools |
|---|---|
| Process/resource view | `top`, `htop`, `ps`, `pidstat` |
| Network sockets | `ss -tulpn`, `lsof -i` |
| Logs | `journalctl`, container logs, app log aggregator |
| Disk | `df -h`, `du`, inode checks |
| CPU/memory | `vmstat`, `free`, cgroup/container metrics |
| DNS/connectivity | `dig`, `curl`, `nc`, `traceroute` |

### Debugging Scenario

```text
API latency is high on one instance only.
Check load balancer distribution, CPU steal, memory pressure, GC/log volume,
connection pool wait, DNS failures, and whether the instance is on a bad host.
Remove from rotation if impact continues.
```

### Interview Traps

- Only knowing cloud dashboards and not host-level checks.
- Confusing liveness with readiness.
- Ignoring file descriptor limits and ephemeral port exhaustion.
- No graceful shutdown behavior.

### Performance Considerations

- CPU saturation increases queueing latency.
- Disk or log IO can hurt request paths.
- Too many TCP connections can hit kernel limits.

### Scalability And Reliability

- Systemd/process supervisors restart crashed services.
- Containers need resource limits and health checks.
- Kernel/network tuning matters for high-connection services.

### Common Mistakes

- Running with default file descriptor limits.
- No log rotation or ingestion backpressure.
- Not handling SIGTERM.

### Quick Revision

- Be able to debug from app metrics down to host/network signals.
- Know readiness, liveness, resource limits, and graceful shutdown.

---

## Infrastructure Automation

### Concept

Infrastructure automation uses scripts, CI/CD, IaC, config management, and deployment tooling to make environments reproducible and safe.

### Why It Matters In Backend Systems

Manual infrastructure changes are hard to audit and easy to misapply. Trading/backoffice services need predictable deploys, rollback, and configuration control.

### Production Relevance

- Use CI to run tests, linters, migrations checks, and image builds.
- Use IaC for networks, databases, queues, Redis, IAM, and alarms.
- Separate config from code.
- Use canaries/rolling deploys for risky changes.

### Deployment Checklist

```text
1. Build immutable artifact.
2. Run tests and migration checks.
3. Deploy to small slice/canary.
4. Watch error rate, p99 latency, saturation, queue lag.
5. Roll forward or rollback.
6. Record incident/deploy notes if behavior changed.
```

### Interview Traps

- No rollback story.
- Running DB migrations blindly during deploy.
- Secrets stored in repo or logs.
- Manual one-off production fixes.

### Performance Considerations

- Deploys can cause cold caches and connection storms.
- Migrations can lock hot tables.
- Autoscaling needs warmup time.

### Scalability And Reliability

- Automation reduces drift.
- Canary deploys limit blast radius.
- Feature flags separate deploy from release.

### Common Mistakes

- No ownership of alerts after infrastructure changes.
- No dependency/version pinning.
- Config changes not reviewed.

### Quick Revision

- Production automation is about repeatability, auditability, and controlled risk.
- Always mention rollback, canary, config, secrets, and migrations.
