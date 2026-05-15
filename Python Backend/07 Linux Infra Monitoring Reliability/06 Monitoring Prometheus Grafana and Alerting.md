# Monitoring Prometheus Grafana and Alerting

Tags: #monitoring #observability #prometheus #grafana #alerts #backend #reliability

## Why This Matters

Monitoring helps you detect production issues before users or traders report them. For backend services, the goal is not to create many dashboards; the goal is to quickly answer: what is broken, how bad is it, who is affected, and what should we do first?

For trading/back-office systems, always connect monitoring to business signals: order acceptance, rejects, latency, exchange connectivity, queue depth, stale market data, reconciliation failures, and dependency health.

## Metrics vs Logs vs Traces

Metrics are numeric time-series values. They are best for alerting, dashboards, SLOs, capacity trends, and fast incident detection.

Logs are event records. They explain what happened for a specific request, order, session, or failure.

Traces show one request moving across services. They are useful when latency is spread across API, risk checks, DB, queues, and external gateways.

```text
Metrics: Is something wrong? Where? How bad?
Logs: What happened for this request/order?
Traces: Which service or dependency took time?
```

Warning: do not put request IDs, order IDs, or raw user IDs into Prometheus labels. Keep those identifiers in logs/traces and keep metrics aggregated by stable labels such as `service`, `endpoint`, `status`, `venue`, and `instance`.

## Prometheus Basics

Prometheus scrapes metrics from HTTP endpoints, usually `/metrics`, and stores them as time series.

```text
service /metrics -> Prometheus scrape -> PromQL rules -> Alertmanager -> Slack/PagerDuty
```

Example metrics endpoint:

```text
# HELP order_rejections_total Total rejected orders
# TYPE order_rejections_total counter
order_rejections_total{reason="risk_limit",venue="NSE"} 182

# HELP order_router_queue_depth Current pending order queue depth
# TYPE order_router_queue_depth gauge
order_router_queue_depth{venue="NSE"} 14
```

Expected interpretation:

- `order_rejections_total` is a counter. Query it with `rate()` or `increase()` to see reject rate over time.
- `order_router_queue_depth` is a gauge. Query it directly because it represents current state.
- The labels are stable operational dimensions, not per-order identifiers.

## Metric Types

Counters only increase. Use them for requests, errors, reconnects, rejects, and retry attempts.

```promql
rate(http_requests_total{service="order-api"}[5m])
```

This shows per-second request rate over the last five minutes. A sudden drop may mean traffic stopped reaching the service; a sudden spike may explain higher latency.

Gauges move up and down. Use them for queue depth, memory, active connections, DB pool usage, and session state.

```promql
order_router_queue_depth{venue="CME"} > 5000
```

This is useful when a venue-specific backlog is growing.

Histograms store latency/size observations in buckets. Use them for p95/p99 latency.

```promql
histogram_quantile(
  0.99,
  sum by (le, endpoint) (
    rate(http_request_duration_seconds_bucket{service="order-api"}[5m])
  )
)
```

This estimates p99 latency by endpoint. In latency-sensitive systems, p99 is usually more useful than average latency because a small tail can still hurt users or trading workflows.

## Python Backend Metrics Example

```python
from fastapi import FastAPI, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
import time

app = FastAPI()

REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["endpoint", "method", "status"],
)

LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["endpoint"],
)

QUEUE_DEPTH = Gauge(
    "order_queue_depth",
    "Pending orders waiting for exchange submission",
    ["venue"],
)

@app.middleware("http")
async def observe_requests(request, call_next):
    start = time.perf_counter()
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        endpoint = request.url.path
        REQUESTS.labels(endpoint=endpoint, method=request.method, status=status).inc()
        LATENCY.labels(endpoint=endpoint).observe(time.perf_counter() - start)

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

Expected `/metrics` output will include lines like:

```text
http_requests_total{endpoint="/orders",method="POST",status="200"} 42.0
http_request_duration_seconds_bucket{endpoint="/orders",le="0.25"} 40.0
order_queue_depth{venue="CME"} 120.0
```

Justification:

- The counter lets you calculate request and error rates.
- The histogram lets you calculate percentile latency.
- The gauge shows current backlog.
- The labels help isolate endpoint and venue without creating one metric series per order.

Warning: if URLs include IDs, prefer route templates like `/orders/{id}` instead of raw paths like `/orders/12345`, otherwise label cardinality can grow quickly.

## Scraping and Exporters

Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: "order-router"
    scrape_interval: 5s
    static_configs:
      - targets:
          - "order-router-01:9000"
          - "order-router-02:9000"
```

Expected result in Prometheus:

```text
up{job="order-router",instance="order-router-01:9000"} 1
up{job="order-router",instance="order-router-02:9000"} 1
```

Interpretation: `up == 1` means Prometheus can scrape the target. `up == 0` means the metrics endpoint is unreachable or failing, not necessarily that the application business path is down.

Exporters expose metrics for systems that do not expose Prometheus metrics themselves:

- `node_exporter`: CPU, memory, disk, network, file descriptors.
- `postgres_exporter`: DB connections, locks, replication lag.
- `redis_exporter`: memory, evictions, command latency.
- Custom exporter: exchange session state, sequence gaps, heartbeat lag.

## Useful PromQL

Error percentage:

```promql
100 *
sum(rate(http_requests_total{service="order-api",status=~"5.."}[5m]))
/
sum(rate(http_requests_total{service="order-api"}[5m]))
```

Expected output:

```text
4.8
```

Interpretation: 4.8% of requests returned 5xx in the last five minutes. If the SLO threshold is 1% or 2%, this is page-worthy when sustained.

Queue depth by venue:

```promql
max by (venue) (order_queue_depth{service="exchange-writer"})
```

Example output:

```text
{venue="CME"} 8200
{venue="NSE"} 12
```

Interpretation: this is likely venue-specific, not a global order routing issue.

Exchange disconnects:

```promql
increase(exchange_disconnects_total[10m])
```

This shows how many disconnects happened in the last ten minutes. During market hours, even a small number may be important if order routing depends on that session.

## Grafana Basics

Grafana visualizes metrics, logs, and traces. A good backend dashboard is arranged around incident questions, not around tool features.

A useful order API dashboard usually has:

- Traffic, 5xx rate, p95/p99 latency, and timeouts.
- Orders accepted/rejected, reject reasons, and venue routing failures.
- DB pool usage, DB query latency, cache latency, and queue lag.
- CPU, memory, file descriptors, sockets, and restarts.
- Logs panel filtered by service and severity.
- Deploy annotations and links to runbooks.

Incident workflow for an order latency spike:

1. Check request rate to see if traffic changed.
2. Check p99 by endpoint to see if the issue is broad or route-specific.
3. Check error and timeout rates.
4. Check queue depth and dependency latency.
5. Check CPU, memory, file descriptors, and restarts.
6. Check deploy annotations.
7. Jump to logs/traces for representative slow requests.

Warning: dashboards with only CPU and memory miss many business outages. Include application and workflow metrics.

## Alerting Systems

Alerts turn monitoring signals into human action. A good alert has impact, severity, scope, current value, threshold, owner, dashboard link, and first response.

Example alert:

```yaml
groups:
  - name: order-api.rules
    rules:
      - alert: OrderApiHighErrorRate
        expr: |
          100 *
          sum(rate(http_requests_total{service="order-api",status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total{service="order-api"}[5m]))
          > 2
        for: 5m
        labels:
          severity: critical
          service: order-api
        annotations:
          summary: "Order API 5xx rate above 2%"
          runbook: "Check deploys, logs, dependency latency, DB pool, and exchange connectivity."
```

Justification:

- The expression uses a percentage, not raw error count.
- `for: 5m` avoids paging for one short spike.
- The alert points to likely first checks.
- Severity is tied to user/business impact.

Warning: page on symptoms first, such as error rate, latency, stale data, and undrained queues. Cause alerts like CPU high are useful, but they should usually support diagnosis rather than be the main page.

## Common Mistakes

- Using average latency instead of p95/p99.
- Alerting on every exception without rate, scope, or impact.
- Missing queue depth, stale data age, or business flow metrics.
- No owner or runbook in alerts.
- No deploy annotations on dashboards.
- High-cardinality labels such as `order_id`, `request_id`, or raw path IDs.

## Quick Revision

- Metrics detect and quantify; logs explain; traces localize distributed latency.
- Prometheus scrapes `/metrics`; Grafana visualizes; Alertmanager routes alerts.
- Counters need `rate()` or `increase()`, gauges are current values, histograms support p95/p99.
- Good alerts are actionable and tied to user/business impact.
- For backend/HFT systems, monitor latency, error rate, queues, rejects, stale data, exchange connectivity, restarts, and saturation.
