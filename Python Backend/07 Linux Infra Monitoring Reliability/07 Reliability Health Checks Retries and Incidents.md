# Reliability Health Checks Retries and Incidents

Tags: #reliability #health-checks #retries #fault-tolerance #incidents #uptime #slo

## Why This Matters

Backend systems rarely fail in one clean way. They fail through slow dependencies, bad deploys, queue buildup, exchange disconnects, stale data, missing timeouts, and overloaded hosts.

Reliability means the system detects failure quickly, limits blast radius, recovers safely, and gives engineers enough evidence to understand what happened.

## Uptime, SLI, SLO, SLA

Uptime should mean the business path works, not just that a process exists.

```text
Process uptime: process is running
Endpoint uptime: HTTP/TCP endpoint responds
Functional uptime: service can perform the real operation
External uptime: users/dependencies can reach it through real network paths
```

Example:

```text
SLI: percentage of /orders requests that complete successfully under 100ms
SLO: 99.9% during market hours
SLA: client-facing commitment, if contractual
```

Justification: defining the SLI first prevents vague answers like "99.9% uptime" without saying what counts as available.

Warning: a service can return `200 OK` on `/health` while order routing, risk checks, or exchange sessions are broken.

## Health Checks

Health checks tell load balancers, orchestrators, and humans whether a service should stay running and receive traffic.

### Liveness

Liveness answers: should this process be restarted?

Example:

```bash
curl -fsS --max-time 1 http://127.0.0.1:8080/live
```

Expected output:

```json
{"status":"alive"}
```

Interpretation: the local process is responsive. This should be cheap and mostly local.

Warning: do not make liveness depend on every downstream dependency. A database blip should not restart every healthy API instance.

### Readiness

Readiness answers: should this instance receive traffic?

```python
from fastapi import FastAPI, Response

app = FastAPI()

state = {
    "db_ready": False,
    "kafka_ready": False,
    "risk_snapshot_age_seconds": 999,
}

@app.get("/ready")
def ready():
    if not state["db_ready"]:
        return Response("db not ready", status_code=503)
    if not state["kafka_ready"]:
        return Response("kafka not ready", status_code=503)
    if state["risk_snapshot_age_seconds"] > 2:
        return Response("risk snapshot stale", status_code=503)
    return {"status": "ready"}
```

Expected outputs:

```text
HTTP 503 db not ready
HTTP 503 risk snapshot stale
HTTP 200 {"status":"ready"}
```

Interpretation: the instance receives traffic only when required state is available and fresh.

Justification:

- DB and Kafka may be hard dependencies for order acceptance.
- Stale risk data can be unsafe.
- Readiness failure removes the instance from traffic without necessarily restarting it.

## Retries

Retries repeat an operation when the failure may be temporary.

Retry examples that may be safe:

- transient timeout;
- temporary `503`;
- connection reset;
- leader failover;
- rate limit after a delay.

Do not retry blindly:

- validation failures;
- authentication failures;
- risk rejections;
- non-idempotent writes;
- operations where the external side effect is unknown.

Production pattern:

```text
small max attempts + timeout per attempt + exponential backoff + jitter + total deadline + idempotency
```

Python example:

```python
import random
import time

def retry_call(fn, *, attempts=3, base_delay=0.05, max_delay=0.5):
    last_error = None
    for attempt in range(attempts):
        try:
            return fn()
        except TimeoutError as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            delay = min(max_delay, base_delay * (2 ** attempt))
            jitter = random.uniform(0, delay * 0.25)
            time.sleep(delay + jitter)
    raise last_error
```

Expected behavior:

```text
attempt 1 fails -> wait about 50ms plus jitter
attempt 2 fails -> wait about 100ms plus jitter
attempt 3 fails -> raise the last TimeoutError
```

Justification:

- Backoff reduces pressure on the dependency.
- Jitter prevents all clients retrying at the same time.
- A small attempt limit prevents long tail latency.

Warning: this blocking `time.sleep()` version is for synchronous code. In async request handlers, use async-aware retry logic.

## Idempotency and Trading Operations

Idempotency means repeating an operation has the same effect as doing it once.

Unsafe:

```python
send_order(order)
send_order(order)  # may create a duplicate live order
```

Safer:

```python
order.client_order_id = "strategyA-20260514-000123"
send_order(order)
```

If the response is unknown, query order status by `client_order_id` before resubmitting.

Justification: a timeout does not prove the exchange rejected the order. It may have accepted it and the acknowledgement may have been lost.

Warning: for order placement, unknown state is a real production state. Treat it with reconciliation, not blind retries.

## Circuit Breaker

A circuit breaker stops calls to a failing dependency temporarily.

```text
Closed: calls allowed
Open: calls fail fast or use fallback
Half-open: limited test calls check recovery
```

Simple sketch:

```python
from enum import Enum
import time

class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold: int, cooldown_seconds: float):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failures = 0
        self.opened_at = 0.0
        self.state = State.CLOSED

    def allow_request(self) -> bool:
        if self.state == State.CLOSED:
            return True
        if time.monotonic() - self.opened_at >= self.cooldown_seconds:
            self.state = State.HALF_OPEN
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.state = State.CLOSED

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.state = State.OPEN
            self.opened_at = time.monotonic()
```

Expected behavior:

```text
closed -> repeated failures -> open
open -> cooldown passes -> half_open
half_open -> success -> closed
half_open -> failure -> open
```

Justification: the caller fails fast instead of filling thread pools, connection pools, and queues while a dependency is already unhealthy.

Warning: fallback must be business-safe. If risk checks are down, the safe response may be to reject new orders, not accept them without validation.

## Fault Tolerance

Fault tolerance is controlled behavior under failure.

Useful patterns:

- Redundancy: multiple instances behind a load balancer.
- Failover: switch to a standby dependency or gateway.
- Bulkheads: separate pools/queues per dependency or venue.
- Backpressure: slow or reject work when the system is saturated.
- Durable queues: preserve work across process failure.
- Reconciliation: verify external state after ambiguous outcomes.

Example critical order path:

```text
client -> API -> auth -> risk -> persistence -> router -> exchange gateway -> exchange
```

Reliability design:

- timeouts at every network boundary;
- idempotency key or client order ID;
- bounded retries where safe;
- circuit breaker around risk/exchange dependencies;
- per-venue queues and worker pools;
- metrics for latency, errors, queue depth, stale data, reconnects;
- structured logs with request/order IDs;
- reconciliation job for ambiguous exchange state;
- fail-closed behavior when risk state is unknown.

## Incident Debugging

Use a consistent order during incidents:

1. Confirm alert and impact.
2. Narrow blast radius by service, endpoint, venue, region, instance, or client.
3. Check recent deploys, config changes, and traffic changes.
4. Inspect metrics: traffic, errors, latency, saturation.
5. Inspect dependencies: DB, cache, queue, exchange, network.
6. Check logs around the start time.
7. Mitigate with the lowest-risk action.
8. Verify recovery with metrics and external checks.
9. Communicate status.
10. Capture follow-ups.

Command workflow:

```bash
systemctl status order-router
journalctl -u order-router --since "30 min ago" -p warning

pid="$(pgrep -f order-router | head -1)"
top -p "$pid"
ps -o pid,ppid,stat,%cpu,%mem,etime,cmd -p "$pid"
free -h
df -h

ss -tanp | grep "$pid"
ss -tan | awk 'NR > 1 {print $1}' | sort | uniq -c | sort -nr

grep -E "ERROR|timeout|disconnect|reconnect|order_rejected" /var/log/order-router/app.log | tail -100
```

Example output:

```text
P99 latency: 1800ms
order_router_queue_depth{venue="CME"} 5000
logs: error=exchange_timeout
ss: many SYN-SENT connections
```

Interpretation: likely exchange gateway or network dependency issue, not just CPU-bound application code.

Possible mitigation:

- stop unsafe routing to the affected venue;
- open circuit breaker or reduce send rate;
- fail over only if split-brain safe;
- stop unbounded retries;
- reconcile open orders after recovery.

## Common Reliability Failures

### Retry Storm

```text
Dependency slows down -> callers retry -> traffic multiplies -> dependency gets worse.
```

Fix with bounded retries, backoff, jitter, deadlines, retry budgets, circuit breakers, and bulkheads.

### Unbounded Queue

```text
Downstream slows -> queue grows -> memory grows -> process OOMs.
```

Fix with queue limits, backpressure, load shedding, and queue depth/age alerts.

### Missing Timeout

```text
Requests hang -> workers block -> latency rises -> service becomes unavailable.
```

Fix with connect/read/overall deadlines and pool monitoring.

### Bad Health Check

```text
Health returns 200 while required state is broken, or liveness restarts healthy pods during a dependency blip.
```

Fix by separating liveness, readiness, startup checks, and dependency alerts.

## Quick Revision

- Liveness decides restart; readiness decides traffic eligibility.
- Retries need limits, backoff, jitter, deadlines, and idempotency awareness.
- Circuit breakers prevent cascading failure by failing fast.
- Fault tolerance uses redundancy, isolation, timeouts, backpressure, and recovery workflows.
- Incident handling should narrow blast radius, mitigate safely, and preserve enough evidence.
