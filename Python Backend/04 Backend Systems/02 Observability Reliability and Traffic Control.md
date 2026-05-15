# Observability, Reliability, And Traffic Control

Tags: #backend #observability #reliability #logging #monitoring #retries #ratelimits #interview

Interview lens: explain how you would know the system is failing, how you limit blast radius, and how clients should behave during partial failure.

---

## Logging Systems

### Concept

Logging records discrete events. Production backend logs should be structured, searchable, correlated, and safe.

### Why It Matters In Backend Systems

Logs are often the fastest way to answer: what request failed, for which account/order, on which instance, and after which downstream call?

### Production Relevance

- Use JSON/structured logs for centralized systems.
- Include `request_id`, `order_id`, `account_id`, `venue`, and dependency names when relevant.
- Avoid secrets, tokens, raw PII, and excessive payload logging.
- Log at meaningful levels: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`.

### Backend Example

```python
import logging
import time

logger = logging.getLogger("orders")

async def submit_order(order: Order, request_id: str) -> ExchangeAck:
    start = time.perf_counter()
    try:
        ack = await exchange_client.send_order(order)
    except TimeoutError:
        logger.warning(
            "exchange_submit_timeout",
            extra={
                "request_id": request_id,
                "client_order_id": order.client_order_id,
                "venue": order.venue,
                "symbol": order.symbol,
            },
        )
        raise

    logger.info(
        "exchange_submit_ack",
        extra={
            "request_id": request_id,
            "client_order_id": order.client_order_id,
            "venue": order.venue,
            "latency_ms": round((time.perf_counter() - start) * 1000, 2),
        },
    )
    return ack
```

### Interview Traps

- Saying "just log everything".
- Logging only error strings without identifiers.
- Logging stack traces for expected validation failures.
- Forgeting that missing logs are also a production bug.

### Performance Considerations

- Synchronous logging can hurt p99 latency.
- Large payload logs increase cost and slow ingestion.
- High-cardinality fields are useful in logs but dangerous in metrics.
- Use sampling for noisy success paths.

### Scalability And Reliability

- Centralized logging enables incident response across instances.
- Correlation IDs connect API logs, worker logs, and downstream calls.
- Logs should degrade gracefully if the log sink is slow.

### Common Mistakes

- No stable event names.
- Different services use different request ID headers.
- Sensitive data in logs.

### Quick Revision

- Logs explain specific events; metrics explain trends; traces explain request paths.
- Always log enough context to debug without leaking secrets.

---

## Monitoring Basics

### Concept

Monitoring measures system health through metrics, checks, dashboards, and alerts.

### Why It Matters In Backend Systems

Backend teams are judged by detection and recovery, not just code correctness. Monitoring tells you when users, trading flows, or internal operations are impacted.

### Production Relevance

- Metrics: numeric time series such as QPS, latency, error rate, queue depth.
- Logs: event details for debugging.
- Traces: request path across services.
- Health checks: machine-readable liveness/readiness.
- Alerts: actionable notifications for symptoms, not every internal oddity.

### Health Check Example

```python
@app.get("/health/live")
async def live():
    return {"status": "ok"}

@app.get("/health/ready")
async def ready():
    db_ok = await db.ping(timeout=0.2)
    redis_ok = await redis.ping()
    if not db_ok or not redis_ok:
        return JSONResponse({"status": "not_ready"}, status_code=503)
    return {"status": "ready"}
```

### Prometheus Metric Example

```python
from prometheus_client import Counter, Histogram

orders_created = Counter("orders_created_total", "Orders accepted by API", ["venue"])
order_latency = Histogram("order_create_seconds", "Order create latency")

async def create_order(order: OrderCreate):
    with order_latency.time():
        result = await order_service.create(order)
    orders_created.labels(venue=order.venue).inc()
    return result
```

### Interview Traps

- Alerting on CPU only while user-facing errors go unnoticed.
- No p95/p99 latency tracking.
- Health checks that always return `200` even when dependencies are down.
- Dashboards with no ownership or runbook.

### Performance Considerations

- Metrics should be cheap and bounded in cardinality.
- Avoid labels like raw `order_id`, `user_id`, or `request_id`.
- Scrape intervals and histogram buckets affect cost and usefulness.

### Scalability And Reliability

- RED metrics for APIs: rate, errors, duration.
- USE metrics for resources: utilization, saturation, errors.
- Alert on symptoms: elevated error rate, sustained p99 latency, queue lag, failed exchange sessions.

### Common Mistakes

- Too many noisy alerts causing alert fatigue.
- No SLO or "what good looks like".
- No runbook linked from alerts.

### Quick Revision

- Logs debug events, metrics detect trends, traces locate cross-service latency.
- Alert on user impact and unrecoverable automation failures.

---

## Retries And Timeouts

### Concept

Timeouts bound waiting. Retries repeat an operation after transient failure. Both require deadlines and idempotency.

### Why It Matters In Backend Systems

Networks, databases, Redis, exchanges, and internal services fail partially. Without timeouts, requests hang. Without careful retries, you can multiply load or duplicate side effects.

### Production Relevance

- Every outbound call should have a timeout.
- Retry only transient failures.
- Use exponential backoff with jitter.
- Cap attempts and total elapsed time.
- Make write operations idempotent before retrying.

### Retry Wrapper Example

```python
import asyncio
import random
import time

async def retry_transient(call, *, attempts: int = 3, base_delay: float = 0.05, deadline: float = 0.5):
    started = time.monotonic()
    last_error: Exception | None = None

    for attempt in range(attempts):
        remaining = deadline - (time.monotonic() - started)
        if remaining <= 0:
            break
        try:
            return await asyncio.wait_for(call(), timeout=remaining)
        except (TimeoutError, ConnectionError) as exc:
            last_error = exc
            if attempt == attempts - 1:
                break
            delay = min(base_delay * (2 ** attempt), remaining)
            await asyncio.sleep(delay * random.uniform(0.5, 1.5))

    raise TimeoutError("operation failed after retry budget") from last_error
```

### Interview Traps

- Retrying non-idempotent writes.
- Retrying immediately with no jitter.
- Having per-call timeouts but no end-to-end deadline.
- Retrying `400`/validation errors.

### Performance Considerations

- Retries increase load during incidents.
- Hedged requests reduce tail latency but increase duplicate work.
- Short timeouts can cause false failures; long timeouts consume resources.

### Scalability And Reliability

- Backoff and jitter reduce synchronized retry storms.
- Circuit breakers stop hammering unhealthy dependencies.
- Deadlines preserve capacity for healthy traffic.

### Common Mistakes

- Infinite retries in workers.
- No visibility into retry counts.
- Retrying through every service layer, multiplying attempts.

### Quick Revision

- Timeouts prevent hanging. Retries handle transient failure. Idempotency makes retries safe.
- Always discuss retry storms in interviews.

---

## Rate Limiting

### Concept

Rate limiting restricts request volume per client, token, account, IP, route, or operation.

### Why It Matters In Backend Systems

It protects APIs from abuse, accidental client loops, expensive queries, and overload that would hurt other users.

### Production Relevance

- Public APIs use per-user/API-key limits.
- Internal services use limits to avoid cascading failure.
- Trading systems may rate-limit order entry to meet venue limits.
- Rate limits should return `429` with retry guidance.

### Algorithms

| Algorithm | Good for | Tradeoff |
|---|---|---|
| Fixed window | Simple quotas | Boundary bursts |
| Sliding window | Smoother limits | More storage/compute |
| Token bucket | Bursts with average rate | Needs careful refill logic |
| Leaky bucket | Constant processing rate | Can add queueing latency |

### Redis Token Bucket Sketch

```python
import time

async def allow_request(redis, key: str, *, rate_per_sec: int, burst: int) -> bool:
    now = time.time()
    bucket = await redis.hgetall(key)
    tokens = float(bucket.get("tokens", burst))
    updated_at = float(bucket.get("updated_at", now))

    tokens = min(burst, tokens + (now - updated_at) * rate_per_sec)
    if tokens < 1:
        await redis.hset(key, mapping={"tokens": tokens, "updated_at": now})
        await redis.expire(key, 60)
        return False

    await redis.hset(key, mapping={"tokens": tokens - 1, "updated_at": now})
    await redis.expire(key, 60)
    return True
```

In production, make the update atomic with Lua or a Redis transaction.

### Interview Traps

- Implementing distributed rate limits with local process memory only.
- Ignoring clock and atomicity issues.
- No plan for Redis outage.
- Applying one global limit to all endpoints regardless of cost.

### Performance Considerations

- Rate limiting adds latency to every protected request.
- Redis round trips can become a bottleneck.
- Local pre-buckets can reduce central calls but weaken strictness.

### Scalability And Reliability

- Distributed limits need shared state or approximate algorithms.
- Fail-open preserves availability but risks overload.
- Fail-closed protects capacity but can reject valid traffic.

### Common Mistakes

- No per-route weighting.
- No headers showing remaining quota.
- No separate limits for expensive admin/export endpoints.

### Quick Revision

- Rate limiting is overload protection and fairness.
- Token bucket is a common answer; mention atomic Redis/Lua for distributed systems.

---

## Production Incident Debugging Pattern

Use this structure in interviews:

1. Confirm user impact: error rate, latency, dropped orders, stale dashboard, queue lag.
2. Scope by dimension: endpoint, account, venue, region, instance, deploy version.
3. Check recent changes: deploys, config, schema, dependency, traffic spike.
4. Inspect metrics first, then traces/logs for exemplars.
5. Mitigate before root cause if impact is ongoing.
6. Add a follow-up fix: tests, alert, dashboard, runbook, backpressure, timeout, or limit.

Quick answer example:

```text
If p99 latency spikes on order creation, I first compare API latency, DB latency,
exchange latency, and queue lag. If only one dependency is slow, I enforce deadlines
and shed non-critical traffic. If all endpoints are slow, I check CPU, connection pools,
GC, deploy version, and load balancer distribution.
```
