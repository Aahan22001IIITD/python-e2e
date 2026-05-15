# Reliability Health Checks Retries and Incidents

Tags: #reliability #health-checks #retries #fault-tolerance #incidents #uptime #slo

## Why This Matters

Backend/HFT systems fail through latency spikes, partial dependency failures, exchange disconnects, bad deploys, queue buildup, and resource exhaustion. Reliability engineering is about designing systems that detect, isolate, recover from, and learn from failures.

## Health Checks

### Concept

Health checks are endpoints or commands used by load balancers, orchestration systems, and humans to determine whether a service can run and serve traffic.

Common endpoint:

```bash
curl -fsS --max-time 2 http://127.0.0.1:8080/health
```

### Liveness Checks

Liveness answers: "Should this process be restarted?"

Example response:

```json
{"status":"alive"}
```

Use liveness for process deadlocks, stuck event loops, or unrecoverable states. Do not make liveness depend on every downstream dependency, or you may restart healthy services during a dependency outage.

### Readiness Checks

Readiness answers: "Should this instance receive traffic?"

Example:

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "exchange_session": "connected",
    "warm_cache": "ok"
  }
}
```

Use readiness to remove an instance from load balancing when it cannot safely serve.

### Backend API Health Monitoring

Practical health script:

```bash
#!/usr/bin/env bash
set -euo pipefail

URL="${1:-http://127.0.0.1:8080/ready}"
curl -fsS --max-time 2 "$URL" | grep -q '"status":"ready"'
```

### Production Mistakes

- Health check returns `200` even when dependencies are broken.
- Health check performs expensive database queries.
- Liveness depends on external services and causes restart storms.
- Health checks have no timeout.
- Readiness does not fail during warmup.

## Retries and Recovery

### Concept

Retries handle temporary failures: network blips, transient `503`, timeouts, leader failover, connection resets. Bad retries amplify outages.

### Retry Strategy

Use:

- Small max attempts.
- Timeout per attempt.
- Exponential backoff.
- Jitter.
- Retry only safe/idempotent operations unless deduplication exists.

Python example:

```python
import random
import time

def retry_call(fn, attempts=3, base_delay=0.05):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except TimeoutError as exc:
            last_error = exc
            if attempt == attempts:
                break
            delay = base_delay * (2 ** (attempt - 1))
            delay += random.uniform(0, delay)
            time.sleep(delay)
    raise last_error
```

### Backend Trading Caution

Do not blindly retry order placement unless the operation has an idempotency key or exchange/client order ID.

Bad:

```python
send_order(order)
send_order(order)  # may create duplicate live order
```

Better:

```python
order.client_order_id = "strategyA-20260514-000123"
send_order(order)
```

If response is unknown, query order status by client order ID before resubmitting.

### Circuit Breaker Basics

A circuit breaker stops calls to a failing dependency temporarily.

States:

- Closed: calls allowed.
- Open: calls blocked/fail fast.
- Half-open: limited probes to test recovery.

Production relevance:

- Prevents thread/connection pool exhaustion.
- Reduces cascading failure.
- Gives dependency time to recover.

Interview example:

```text
If exchange gateway timeouts spike, continuing unlimited retries may fill queues and exhaust worker threads. A circuit breaker fails fast, emits alerts, and lets the system degrade safely.
```

## Fault Tolerance Basics

### Redundancy

Run multiple instances so one failure does not take down the service.

```text
load balancer -> order-router-01
              -> order-router-02
              -> order-router-03
```

### Graceful Degradation

When one dependency is down, preserve critical behavior.

Examples:

- Disable non-critical analytics but keep order routing.
- Serve cached reference data if the source is temporarily down.
- Switch to read-only mode when writes are unsafe.
- Reject new orders safely if risk checks are unavailable.

### Failure Isolation

Prevent one bad subsystem from exhausting shared resources.

Examples:

- Separate thread pools for market data and order routing.
- Separate queues per exchange.
- Timeouts on all dependency calls.
- Bulkheads for slow clients.
- Resource limits per container/service.

### Backend Reliability Engineering

Design around:

- Timeouts.
- Backpressure.
- Queue bounds.
- Idempotency.
- Observability.
- Controlled deploys.
- Fast rollback.
- Runbooks.

## Incident Debugging

### Production Outage Workflow

1. Confirm impact.
2. Identify affected service, host, route, customer, or exchange.
3. Check recent changes.
4. Inspect metrics for traffic, error rate, latency, saturation.
5. Inspect logs for concrete errors and correlation IDs.
6. Check process/service state.
7. Mitigate first if impact is severe.
8. Preserve evidence for root cause.
9. Communicate status and next action.

### Command Workflow

```bash
# Service state
systemctl status order-router
journalctl -u order-router --since "30 min ago" -p warning

# Process and host pressure
pid="$(pgrep -f order-router | head -1)"
top -p "$pid"
ps -o pid,ppid,stat,%cpu,%mem,etime,cmd -p "$pid"
free -h
df -h

# Network state
ss -tanp | grep "$pid"
ss -tan | awk 'NR > 1 {print $1}' | sort | uniq -c | sort -nr

# Logs
grep -E "ERROR|timeout|disconnect|reconnect|order_rejected" /var/log/order-router/app.log | tail -100
```

### Logs + Metrics Correlation

Example incident:

- Grafana shows P99 latency from `40ms` to `1800ms`.
- Queue depth increased from `10` to `5000`.
- Logs show `exchange_timeout`.
- `ss` shows many `SYN-SENT` connections.

Conclusion: likely exchange gateway/network dependency issue, not CPU-bound app bug.

Mitigation:

- Fail over exchange gateway if available.
- Open circuit breaker or reduce send rate.
- Stop unbounded retries.
- Keep order state consistent.
- Communicate degraded routing.

### Debugging Crashed Services

```bash
systemctl status risk-engine
journalctl -u risk-engine --since "1 hour ago"
systemctl show risk-engine --property=NRestarts
dmesg -T | grep -i "killed process"
```

Common causes:

- Bad config.
- OOM kill.
- Unhandled exception.
- Permission issue.
- Port conflict.
- Missing secret/file.
- Dependency unavailable at startup.

### Identifying Bottlenecks

CPU:

```bash
top -p "$pid"
ps aux --sort=-%cpu | head
```

Memory:

```bash
free -h
ps aux --sort=-%mem | head
```

Disk:

```bash
df -h
du -sh /var/log/*
lsof | grep deleted
```

Network:

```bash
ss -tanp
curl -v --max-time 2 http://dependency:8080/health
```

## Uptime and Reliability

### SLA, SLO, SLI

- SLI: measured signal, e.g. successful order API requests.
- SLO: target, e.g. 99.95% success over 30 days.
- SLA: contractual promise with consequences.

Backend example:

```text
SLI: percentage of /orders requests completing successfully under 100ms
SLO: 99.9% during market hours
```

### Reducing Downtime

Practices:

- Rolling deploys.
- Blue/green or canary deploys.
- Fast rollback.
- Backward-compatible DB migrations.
- Health-gated deployment.
- Dependency timeouts.
- Circuit breakers.
- Capacity headroom.
- Runbooks and ownership.

### Deployment Reliability

Safe deploy checklist:

```bash
# Before deploy
systemctl status order-router
curl -fsS http://127.0.0.1:8080/ready

# After deploy
systemctl status order-router
journalctl -u order-router --since "5 min ago" -p warning
curl -fsS http://127.0.0.1:8080/ready
```

Watch metrics:

- Error rate.
- Latency.
- Queue depth.
- Restarts.
- Dependency failures.
- Domain metrics like rejects or feed gaps.

## Common Backend Reliability Failures and Fixes

### Retry Storm

Symptoms:

- Dependency down.
- App retries aggressively.
- CPU/threads/connections spike.
- Queue grows.

Fix:

- Timeouts.
- Exponential backoff with jitter.
- Circuit breaker.
- Retry budget.
- Backpressure.

### Unbounded Queue

Symptoms:

- Memory grows.
- Latency grows.
- OOM kill.

Fix:

- Bound queue size.
- Apply backpressure.
- Drop/degrade non-critical work.
- Alert on queue depth.

### Missing Timeout

Symptoms:

- Threads stuck.
- Requests hang.
- `CLOSE-WAIT` or saturated pool.

Fix:

- Set connect/read/request timeouts.
- Monitor pool usage.
- Fail fast where safe.

### Bad Health Check

Symptoms:

- Load balancer sends traffic to broken instance.
- Orchestration restarts healthy instances during dependency outage.

Fix:

- Separate liveness and readiness.
- Add timeouts.
- Include critical dependencies in readiness only.

## Interview Questions and Traps

- "Difference between liveness and readiness?"
  - Answer: Liveness decides whether to restart a process; readiness decides whether the instance should receive traffic.
- "When are retries dangerous?"
  - Answer: Retries are dangerous for non-idempotent writes, overload, long dependency outages, and operations with unknown external side effects.
- "How do you prevent duplicate order submission?"
  - Answer: Use client order IDs/idempotency keys, durable intent records, response replay, and reconciliation after timeout.
- "What is a circuit breaker?"
  - Answer: A circuit breaker stops calls to an unhealthy dependency after failure thresholds, then probes recovery in a controlled half-open state.
- "How do you debug a production outage?"
  - Answer: Confirm impact, check dashboards, narrow blast radius, review deploys, inspect logs/traces, mitigate safely, and preserve evidence.
- "What metrics indicate a queue bottleneck?"
  - Answer: Rising depth, oldest message age, consumer lag, processing latency, retry/DLQ rate, and stale business events.
- "What is graceful degradation?"
  - Answer: Keeping critical behavior safe by disabling nonessential features, serving cached/read-only data, rate limiting, or rejecting risky operations.
- "Difference between SLA, SLO, and SLI?"
  - Answer: SLA is the external promise, SLO is the internal target, and SLI is the measured signal used to evaluate reliability.

Trap: saying "just retry" for trading operations. Mention idempotency and unknown execution state.

## Best Practices

- Every network call needs a timeout.
- Retries need limits, backoff, jitter, and idempotency awareness.
- Health checks should be cheap and meaningful.
- Alert on user-impacting symptoms.
- Preserve evidence before restarts when possible.
- Keep runbooks close to alerts.
- Design for partial failure, not only total failure.

## Common Mistakes

- Infinite retries.
- No idempotency key.
- Unbounded queues.
- Health checks that always return `200`.
- Alerting only on CPU/memory.
- Deploying all instances at once.
- Restarting first and investigating later.
- No rollback path.

## Quick Revision

- Liveness decides restart; readiness decides traffic eligibility.
- Retries help transient failures but can amplify outages.
- Circuit breakers prevent cascading failure.
- Fault tolerance uses redundancy, isolation, timeouts, backpressure, and graceful degradation.
- SLOs should map to user/business impact.
- Incident debugging combines metrics, logs, process state, network state, and recent changes.
# Reliability Health Checks Retries and Incidents

Tags: #reliability #healthchecks #retries #circuitbreaker #faulttolerance #backend #hft #interview

Use this note to answer reliability design and incident debugging questions for backend systems supporting trading operations.

Reliability in interviews should sound practical: know what can fail, how you detect it, how you limit blast radius, and how you recover without making the incident worse.

---

## Uptime Monitoring

### Concept

Uptime monitoring checks whether a service is available from the perspective that matters.

Levels:

- **Process uptime**: process is running.
- **Host/container uptime**: machine or pod is alive.
- **Endpoint uptime**: HTTP/TCP endpoint responds.
- **Functional uptime**: service can perform the business operation.
- **External uptime**: users or dependent systems can reach it through real network paths.

A backend can pass process uptime and still fail functional uptime.

### Why It Matters In Backend Production

Trading systems require low downtime because outages can block orders, stale risk checks, market data updates, reconciliation, or exchange automation workflows.

Examples:

- Order API responds to `/health`, but cannot write to Kafka.
- Exchange gateway process is alive, but FIX session is logged out.
- Risk service responds to ping, but risk snapshot is 30 seconds stale.
- Load balancer routes traffic to a pod that is alive but not warmed up.

Production interview point: availability must be measured from the user/business path, not only from the process.

### SLAs And SLOs Basics

Definitions:

- **SLA**: external promise, often contractual.
- **SLO**: internal target for reliability.
- **SLI**: measured indicator used to evaluate the SLO.

Example:

```text
SLI: percentage of order submission requests that complete successfully under 100ms
SLO: 99.9% over trading hours
SLA: client-facing availability commitment, if contractual
```

Backend-oriented SLIs:

- successful API request rate;
- p99 latency below threshold;
- exchange session availability during market hours;
- maximum market data staleness;
- consumer lag below threshold;
- order queue drain time.

Common trap: saying "99.9% uptime" without defining what counts as available.

### Monitoring Endpoints

Typical endpoints:

- `/live`: process is alive.
- `/ready`: service can receive traffic.
- `/health`: human or monitoring summary.
- `/metrics`: Prometheus metrics.

Production caution: do not make liveness depend on every downstream dependency. If a database blips and liveness kills every pod, you can create a self-inflicted outage.

### Downtime Detection

Useful checks:

```text
blackbox probe -> public/internal API route
Prometheus up == 0 -> scrape target missing
synthetic order check -> non-destructive order validation path
FIX heartbeat monitor -> exchange connectivity
consumer lag monitor -> data processing freshness
```

Production example:

A blackbox monitor calls `/orders/validate` every 10 seconds with a test payload. The service returns `200`, but the monitor also checks response time and validation result. If response time exceeds 200ms for 3 minutes, it alerts as degraded availability, not full outage.

### Production Best Practices

- Monitor from inside and outside the cluster/VPC.
- Measure functional availability, not only HTTP `200`.
- Separate market-hours and off-hours alert policies.
- Track partial outages by venue, endpoint, and region.
- Include synthetic checks for critical paths.
- Tie uptime to SLOs and error budgets when possible.

### Common Mistakes

- Equating process alive with service available.
- One global uptime number hides venue-specific outage.
- Health endpoint always returns `200`.
- Uptime check bypasses authentication/routing layers and misses real failures.
- No synthetic check for order/risk/exchange workflows.

### Quick Revision

- Uptime means the business path works within expected latency.
- Define SLIs before talking about SLOs.
- Monitor availability by endpoint, venue, dependency, and user path.
- Health checks and uptime monitors serve different purposes.

---

## Health Checks

### Concept

Health checks expose whether a service should stay running and whether it should receive traffic.

Types:

- **Liveness**: should the orchestrator restart this process?
- **Readiness**: should this instance receive traffic?
- **Dependency health**: are required dependencies usable?
- **Startup health**: has the process initialized and warmed up?

### Liveness Checks

Liveness answers: "Is this process stuck beyond recovery?"

Good liveness checks:

- event loop/thread is responsive;
- process can serve a simple local request;
- no deadlock detected;
- core worker heartbeat is fresh.

Bad liveness checks:

- fail if database is temporarily slow;
- fail if exchange disconnects;
- fail on any dependency error;
- perform expensive operations.

Production failure:

Database latency spikes for 30 seconds. Liveness checks depend on DB query. Kubernetes restarts every API pod. Connection pools reset, caches cold-start, and the outage becomes worse.

Fix: keep liveness mostly local. Put dependency readiness in readiness checks.

### Readiness Checks

Readiness answers: "Can this instance safely receive traffic?"

Readiness can check:

- config loaded;
- DB connection pool initialized;
- Kafka producer connected;
- required cache warmed;
- exchange session active if the service cannot function without it;
- background workers caught up enough to serve.

Example:

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

Production note: readiness should fail fast and predictably. Do not run a slow full-system diagnostic on every check.

### Dependency Health Checks

Dependency checks are useful, but they need nuance.

Dependency categories:

- **Hard dependency**: service cannot safely operate without it.
- **Soft dependency**: service can degrade gracefully.
- **Startup dependency**: needed to initialize but not every request.
- **Critical path dependency**: affects user-facing operation directly.

Example:

For an order API:

- DB for order persistence: hard dependency.
- Risk service: hard dependency for order acceptance.
- Email notification service: soft dependency.
- Analytics stream: soft dependency.

Readiness should not fail because email notifications are down.

### Kubernetes/Backend Relevance

In Kubernetes:

- liveness failure restarts the container;
- readiness failure removes it from service endpoints;
- startup probe prevents slow-starting services from being killed too early.

Interview answer:

"I use liveness for local process health, readiness for traffic safety, and metrics/alerts for broader dependency health. I avoid making liveness dependent on remote systems because it can trigger restart storms."

### Production Examples

Exchange connector:

- Liveness: main event loop heartbeat updated within 1 second.
- Readiness: FIX session logged on and sequence state loaded.
- Dependency health: network path to exchange, credentials valid, heartbeat lag low.

Market data service:

- Liveness: process can accept admin request.
- Readiness: subscribed to required symbols and latest feed timestamp below threshold.
- Metric alert: market data stale by feed/venue.

Order API:

- Liveness: HTTP server responsive.
- Readiness: DB pool, risk service, Kafka producer ready.
- Metric alert: p99 latency, error rate, order reject rate.

### Common Mistakes

- Health endpoint returns `200 OK` no matter what.
- Liveness performs dependency checks and causes restart storms.
- Readiness ignores stale internal state.
- No startup probe for slow initialization.
- Health check is slower than the load balancer timeout.
- Health check has side effects, such as writing to DB or submitting test orders.

### Quick Revision

- Liveness decides restart.
- Readiness decides traffic routing.
- Dependency checks should distinguish hard vs soft dependencies.
- Health checks must be cheap, fast, and side-effect free.

---

## Retries

### Concept

Retries repeat a failed operation when the failure may be transient.

Transient failures:

- network timeout;
- temporary `503`;
- leader election;
- short DB failover;
- connection reset;
- rate-limited upstream after a delay.

Permanent failures:

- invalid order payload;
- authentication failure;
- insufficient balance/risk check failed;
- malformed request;
- unsupported symbol.

Only retry failures that may succeed later.

### Why Retries Matter In Backend Reliability

Distributed systems fail partially. A single dropped packet should not fail an entire workflow if retrying is safe.

But retries can also make incidents worse:

- multiply load on a degraded dependency;
- duplicate non-idempotent operations;
- increase tail latency;
- create retry storms;
- hide real failure rates.

In trading systems, duplicate order submission is a serious risk. Retrying order placement requires idempotency keys, client order IDs, or exchange-level duplicate protection.

### Retry Strategies

Basic strategies:

- fixed delay;
- exponential backoff;
- exponential backoff with jitter;
- bounded retries;
- deadline-based retries;
- retry budget.

Preferred production pattern:

```text
small max attempts + exponential backoff + jitter + total deadline + idempotency
```

Example:

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

Production caveat: blocking `time.sleep()` is wrong inside async request handlers. Use async-aware retry logic for async services.

### Exponential Backoff And Jitter

Backoff reduces pressure on a failing dependency. Jitter prevents synchronized retries.

Without jitter:

```text
100 clients fail at t=0
100 retry at t=100ms
100 retry at t=200ms
100 retry at t=400ms
```

With jitter, retries spread out and reduce thundering herd behavior.

### Retry Storms

A retry storm occurs when many clients retry a failing service and amplify traffic.

Production example:

Risk service latency increases. Order API times out after 100ms and retries 3 times. Incoming traffic is 2,000 requests/sec. Risk service now sees up to 6,000 requests/sec plus original slow work. Latency worsens, queues grow, and the failure cascades.

Fixes:

- set retry limits;
- use backoff with jitter;
- enforce request deadlines;
- add circuit breaker;
- use bulkheads/connection pool limits;
- retry only idempotent operations;
- expose retry count metrics;
- shed load when queue/dependency is saturated.

### Idempotency

Idempotency means repeating the operation has the same effect as doing it once.

Safe to retry:

- `GET` market status;
- validation request;
- publish with idempotent producer;
- order submit with unique `client_order_id` and duplicate handling.

Unsafe to retry blindly:

- submit order without idempotency key;
- transfer funds;
- cancel/replace if state transitions are unclear;
- any operation with side effects and no deduplication.

Interview answer:

"Before retrying an order submission, I need idempotency. I would use a client order ID, persist attempt state, and reconcile with the exchange before deciding whether to resubmit."

### Retry Observability

Track:

- retry attempts total;
- retry success after attempt N;
- retry exhaustion;
- retry latency contribution;
- upstream timeout count;
- duplicate/idempotency conflict count.

Example metrics:

```text
upstream_retries_total{service="order-api", dependency="risk", outcome="success"}
upstream_retries_exhausted_total{service="order-api", dependency="risk"}
```

### Common Mistakes

- Retrying all exceptions.
- Retrying validation/auth errors.
- Infinite retries in background workers.
- No jitter.
- No total deadline.
- Retrying non-idempotent operations.
- Hiding retries from metrics/logs.
- Stacking retries across service layers.

### Quick Revision

- Retry transient failures only.
- Use bounded exponential backoff with jitter.
- Always consider idempotency and deadlines.
- Retries improve resilience but can amplify outages.
- Measure retries as first-class production signals.

---

## Circuit Breaker Concept

### Concept

A circuit breaker protects a service from repeatedly calling a failing dependency.

States:

- **Closed**: calls flow normally.
- **Open**: calls fail fast or use fallback.
- **Half-open**: limited test calls check if dependency recovered.

Purpose: stop cascading failures and give dependencies time to recover.

### Why It Matters In Backend Production

If a downstream service is slow, callers can pile up threads, connections, and queues waiting for timeouts. This can make healthy services fail.

Example:

Order API depends on risk service. Risk service starts timing out. Without a circuit breaker:

- Order API threads block.
- Connection pools fill.
- API latency spikes.
- Load balancer retries.
- More traffic hits risk service.
- Order API becomes unavailable.

With a circuit breaker:

- after enough failures, calls fail fast;
- API can return controlled `503` or "risk unavailable";
- threads are preserved;
- risk service gets breathing room;
- alerts fire with clear dependency failure.

### State Transitions

```text
Closed -> Open:
  failure rate or timeout count exceeds threshold

Open -> Half-open:
  after cooldown period

Half-open -> Closed:
  trial calls succeed

Half-open -> Open:
  trial calls fail
```

### Production Example

For a market data enrichment dependency:

- Closed: normal enrichment call.
- Open: serve quote without enrichment and mark field unavailable.
- Half-open: allow 5 requests/sec to test recovery.

For risk checks:

- Closed: normal risk validation.
- Open: fail order acceptance safely, because accepting orders without risk is not allowed.
- Half-open: test risk service with controlled validation requests.

Interview nuance: fallback depends on business safety. In trading, graceful degradation may mean rejecting new orders, not accepting risk blindly.

### Python-Style Sketch

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

Production note: real circuit breakers usually need rolling windows, concurrency safety, per-dependency/per-venue separation, metrics, and integration with timeouts.

### Observability

Track:

- circuit state by dependency;
- open transitions;
- fail-fast count;
- half-open success/failure;
- fallback usage;
- downstream latency/error rate.

Example:

```text
circuit_breaker_state{dependency="risk", state="open"} 1
circuit_breaker_rejected_total{dependency="risk"} 238
```

### Common Mistakes

- Circuit breaker threshold too sensitive, causing flapping.
- One global breaker for unrelated venues/dependencies.
- No clear fallback behavior.
- Using circuit breaker instead of fixing timeouts.
- No metrics for open/half-open state.
- Opening circuit on caller-side bugs, not dependency failures.
- Letting half-open allow too much traffic.

### Quick Revision

- Circuit breakers prevent cascading failures.
- Closed means normal, open means fail fast, half-open means test recovery.
- Fallback must be safe for the business.
- In trading systems, safe degradation often means stop/route/reject, not guess.

---

## Fault Tolerance Basics

### Concept

Fault tolerance is the ability of a system to continue operating, possibly in degraded mode, when components fail.

Building blocks:

- redundancy;
- replication;
- failover;
- graceful degradation;
- timeouts;
- retries;
- circuit breakers;
- bulkheads;
- backpressure;
- durable queues;
- reconciliation;
- idempotency.

### Why It Matters In Backend Production

Production failures are normal:

- host dies;
- pod restarts;
- network packet loss;
- exchange disconnects;
- DB primary fails over;
- Kafka partition unavailable;
- cache evicts hot keys;
- dependency latency spikes;
- deploy introduces bug.

Fault-tolerant systems limit blast radius and recover predictably.

### Redundancy

Redundancy means multiple components can serve the same role.

Examples:

- multiple API replicas behind a load balancer;
- active/passive exchange gateway;
- multiple Kafka brokers;
- DB primary with replica;
- multiple network paths to exchange.

Tradeoff: redundancy increases complexity. You need health checks, failover rules, state synchronization, and split-brain protection.

### Graceful Degradation

Graceful degradation means serving reduced functionality instead of total failure.

Examples:

- show cached market status when reference data service is down;
- reject new orders safely while allowing cancels;
- disable non-critical analytics writes;
- continue read-only mode during DB primary failover;
- route orders away from one failing venue if business rules allow.

Trading nuance:

Some systems should fail closed. If risk checks are unavailable, accepting orders may be unsafe. Graceful degradation is not always "keep serving everything."

### Failure Recovery

Recovery patterns:

- restart process;
- drain bad instance from load balancer;
- rollback deploy;
- fail over to standby;
- replay messages from durable log;
- reconcile state with source of truth;
- rebuild cache from DB;
- resync FIX sequence numbers.

Example:

Exchange connector disconnects and reconnects. After reconnect:

1. confirm session logon;
2. check expected sequence numbers;
3. request resend if gap exists;
4. block normal routing until sequence state is safe;
5. reconcile open orders;
6. emit metrics/logs for reconnect and recovery duration.

### Replication Basics

Replication copies data to improve availability and durability.

Backend examples:

- DB primary/replica for reads and failover;
- Kafka replication across brokers;
- Redis replica for high availability;
- in-memory cache rebuilt from source of truth;
- active/passive exchange gateway state replication.

Tradeoffs:

- replication lag can serve stale data;
- failover may lose unreplicated writes;
- active/active systems need conflict handling;
- consistency and availability trade off during network partitions.

Interview phrase:

"Replication improves availability, but I would monitor replication lag and be explicit about whether stale reads are acceptable for that path."

### Bulkheads And Backpressure

Bulkheads isolate failures.

Examples:

- separate connection pools per dependency;
- separate queues per venue;
- separate thread pools for order submission and reporting;
- rate limits per client/service;
- one failing venue cannot consume all worker threads.

Backpressure slows or rejects incoming work when the system is saturated.

Examples:

- return `429` or `503` when queue depth is too high;
- stop reading from Kafka temporarily;
- reject non-critical requests;
- shed low-priority traffic before critical traffic.

Production mistake: using one global worker pool for all venues. If one exchange stalls, it consumes all workers and blocks healthy venues.

### Designing Resilient Backend Systems

For a critical order path:

```text
client -> API -> auth -> risk -> order persistence -> router -> exchange gateway -> exchange
```

Reliability design:

- timeouts at every network boundary;
- idempotency key/client order ID;
- bounded retries only where safe;
- circuit breaker around risk/exchange dependencies;
- durable queue between API and router if async design is acceptable;
- per-venue queues and worker pools;
- metrics for latency, errors, queue depth, stale state, reconnects;
- structured logs with request/order/correlation IDs;
- reconciliation job for ambiguous states;
- clear fail-closed behavior when risk or exchange state is unknown.

### Production Tradeoffs

Low latency vs durability:

- synchronous durable writes are safer but slower;
- async queues improve decoupling but add eventual consistency and recovery complexity.

Availability vs correctness:

- accepting orders during risk outage may preserve availability but violate safety;
- rejecting orders protects correctness but reduces availability.

Failover speed vs split-brain risk:

- fast failover reduces downtime;
- unsafe failover can create duplicate sessions/orders.

Retry aggressiveness vs overload:

- more retries may mask transient issues;
- too many retries can collapse dependencies.

### Common Mistakes

- No timeouts, only default library behavior.
- Shared resource pool across unrelated traffic classes.
- Retrying writes without idempotency.
- Assuming failover is safe without testing.
- No reconciliation for ambiguous external state.
- Treating cache as source of truth.
- No runbook for dependency outage.
- Monitoring only infrastructure, not business flow.

### Quick Revision

- Fault tolerance is about controlled behavior under failure.
- Use redundancy, isolation, timeouts, backpressure, and recovery workflows.
- Not every failure should be hidden; some should fail closed.
- In HFT/backend systems, correctness and risk control can matter more than raw availability.

---

## Backend Incident Handling

### Practical Flow

When a production backend incident starts:

1. Confirm alert and impact.
2. Identify affected service, endpoint, venue, region, or client.
3. Check recent deploy/config/traffic changes.
4. Look at golden signals: traffic, errors, latency, saturation.
5. Check dependencies: DB, cache, queue, exchange, network.
6. Look at logs around the start time.
7. Mitigate with the lowest-risk action.
8. Verify recovery using metrics and external checks.
9. Communicate status.
10. Capture follow-ups: bug fix, alert tuning, dashboard gap, runbook gap.

### Example: Exchange Connectivity Loss

Symptoms:

- `exchange_session_up{venue="CME"} == 0`
- order queue depth for CME grows;
- order API still accepts orders;
- trader reports missing acknowledgements.

Immediate actions:

- stop routing new CME orders if unsafe;
- confirm whether cancels are affected;
- check gateway logs for logout/reject/heartbeat timeout;
- check network path and credentials/session state;
- fail over to standby gateway only if split-brain safe;
- reconcile open orders after reconnect.

Root causes:

- exchange-side disconnect;
- network route issue;
- heartbeat thread blocked;
- sequence mismatch;
- credentials/session lockout;
- deploy changed FIX settings.

### Example: API Latency Spike

Symptoms:

- p99 latency above SLO;
- 5xx may be normal;
- DB pool wait high;
- CPU normal.

Debug:

- check endpoint-level latency;
- inspect DB query p99 and connection pool usage;
- look for long transactions/locks;
- compare with request rate;
- inspect recent deploy;
- check slow query logs.

Mitigation:

- rollback bad query/deploy;
- increase pool only if DB can handle it;
- shed low-priority traffic;
- add cache only after root cause is understood.

### Example: Retry Storm

Symptoms:

- upstream timeout count spikes;
- retry metrics spike;
- dependency QPS triples;
- thread pool saturation;
- many requests fail after full timeout.

Mitigation:

- reduce retry attempts via config;
- open circuit breaker;
- increase timeout only if dependency is slow but healthy;
- shed load;
- disable non-critical callers.

Post-incident fixes:

- retry budget;
- jitter;
- circuit breaker;
- dependency-specific bulkhead;
- better alert for retry amplification.

### Quick Revision

- Mitigate before deep root-cause analysis.
- Narrow blast radius early.
- Correlate metrics, logs, deploys, and dependency state.
- Avoid restarts/failovers that can duplicate trading sessions or lose state.
- Recovery is not complete until queues drain and external state is reconciled.

