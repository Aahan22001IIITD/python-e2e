# Monitoring Prometheus Grafana and Alerting

Tags: #monitoring #observability #prometheus #grafana #alerts #backend #reliability

## Why This Matters

Backend/HFT systems need production visibility before users or traders notice failures. Monitoring answers: is the system up, is it correct, is it fast enough, and where is the bottleneck?

Good monitoring is not "many dashboards". It is actionable signals tied to user/business impact.

## Metrics vs Logs vs Traces

### Metrics

Numeric time-series values.

Examples:

- `http_requests_total`
- `http_request_duration_seconds`
- `order_rejections_total`
- `exchange_session_connected`
- `queue_depth`
- `process_resident_memory_bytes`

Use metrics for:

- Alerting.
- Trends.
- SLOs.
- Capacity.
- Fast incident detection.

### Logs

Event records with context.

Use logs for:

- Why a specific request/order failed.
- Stack traces.
- Error details.
- Deployment markers.

### Traces

Request flow across services.

Use traces for:

- Distributed latency.
- Dependency breakdown.
- Cross-service call paths.

Interview answer: metrics tell you something is wrong, logs explain specific failures, traces show where time went across services.

## Observability Basics

Key production questions:

- Is the service up?
- Is it accepting traffic?
- Is latency within target?
- Are error rates normal?
- Are queues/backlogs growing?
- Are dependencies healthy?
- Are exchange sessions connected?
- Did this correlate with deploy/config change?

For trading workflows, add correctness signals:

- Order accepted/rejected counts.
- Exchange disconnects/reconnects.
- Market data gap count.
- Feed lag.
- Position reconciliation failures.
- Risk check latency.

## Uptime Monitoring

External uptime checks:

```bash
curl -fsS --max-time 2 https://api.example.com/health
```

Internal check:

```bash
curl -fsS --max-time 1 http://127.0.0.1:8080/health
```

Uptime alone is insufficient. A service can return `200 OK` while order routing is broken.

Better health response:

```json
{
  "status": "ok",
  "version": "1.42.0",
  "checks": {
    "database": "ok",
    "exchange_session": "connected",
    "queue_depth": 12
  }
}
```

## Prometheus Basics

### Concept

Prometheus scrapes metrics from HTTP endpoints and stores time series. Applications expose `/metrics`; Prometheus periodically pulls them.

Typical flow:

```text
service /metrics -> Prometheus scrape -> rules/alerts -> Alertmanager -> pager/slack
```

### Metrics Endpoint Example

```text
# HELP order_rejections_total Total rejected orders
# TYPE order_rejections_total counter
order_rejections_total{reason="risk_limit",exchange="NSE"} 182

# HELP order_router_queue_depth Current order queue depth
# TYPE order_router_queue_depth gauge
order_router_queue_depth 14
```

Metric types:

- Counter: only increases, e.g. requests, errors, reconnects.
- Gauge: can go up/down, e.g. memory, queue depth, current sessions.
- Histogram: distribution, e.g. latency buckets.

### Python Backend Example

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server

ORDERS = Counter("orders_total", "Orders received", ["exchange"])
REJECTIONS = Counter("order_rejections_total", "Rejected orders", ["reason"])
LATENCY = Histogram("order_route_latency_seconds", "Order routing latency")
QUEUE_DEPTH = Gauge("order_router_queue_depth", "Pending orders")

start_http_server(9000)

def route_order(order):
    ORDERS.labels(exchange=order.exchange).inc()
    with LATENCY.time():
        # route order to exchange
        pass
```

### Scraping

Prometheus config:

```yaml
scrape_configs:
  - job_name: "order-router"
    scrape_interval: 5s
    static_configs:
      - targets:
          - "order-router-01:9000"
          - "order-router-02:9000"
```

Production note: choose scrape interval based on signal needs and cost. Latency-sensitive systems may need fast metrics, but high-cardinality metrics can overload storage.

### Exporters

Exporters expose metrics for systems that do not natively expose Prometheus metrics.

Common exporters:

- Node exporter: CPU, memory, disk, network.
- Blackbox exporter: external HTTP/TCP checks.
- Database exporters: DB health and performance.
- Custom app exporter: domain-specific trading metrics.

### PromQL Examples

Error rate:

```promql
sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))
```

P95 latency:

```promql
histogram_quantile(
  0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, route)
)
```

Queue depth:

```promql
max(order_router_queue_depth)
```

Exchange disconnects:

```promql
increase(exchange_disconnects_total[10m])
```

### Alerting Rule Example

```yaml
groups:
  - name: order-router
    rules:
      - alert: OrderRouterHighErrorRate
        expr: |
          sum(rate(http_requests_total{service="order-router",status=~"5.."}[5m]))
          /
          sum(rate(http_requests_total{service="order-router"}[5m]))
          > 0.02
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Order router 5xx rate above 2%"
          runbook: "Check deploys, logs, dependency timeouts, and exchange connectivity."
```

`for: 5m` prevents paging for a single short spike.

## Grafana Basics

### Concept

Grafana visualizes metrics/logs/traces through dashboards. It helps humans see trends, compare services, and debug incidents.

### Useful Backend Dashboard Panels

- Request rate by route/status.
- P50/P95/P99 latency.
- Error rate by service/route.
- Queue depth/backlog.
- CPU/memory per instance.
- Restarts per service.
- File descriptor usage.
- Exchange session connected status.
- Market data lag.
- Dependency latency/error rate.

### Dashboard Design

Good dashboards answer:

- Is there user/business impact?
- Which service is affected?
- Is the issue traffic, app, host, dependency, or deploy?
- Is it one instance or all instances?
- Is it getting worse?

Bad dashboards:

- Too many panels with no hierarchy.
- No units.
- No thresholds.
- No link to logs/runbooks.
- Only host metrics, no application/business metrics.

### Production Debugging With Grafana

Incident: order latency increased.

Check panels in order:

1. Request/order rate: traffic spike?
2. Error/rejection rate: failures increased?
3. P95/P99 latency: broad or tail-only?
4. Queue depth: backlog growing?
5. CPU/memory/GC: host/app pressure?
6. Dependency latency: exchange/DB/cache slow?
7. Deploy markers: did a version change?

## Alerting Systems

### Concept

Alerts convert monitoring signals into human action. Good alerts are actionable, urgent, and tied to user impact.

### Critical vs Warning

Critical:

- Users/orders affected now.
- Service unavailable.
- Exchange session disconnected during market hours.
- Error rate above SLO threshold.
- Queue depth growing and not draining.

Warning:

- Disk above 80%.
- Memory increasing unusually.
- Cert expires soon.
- Non-critical job failed.
- Single instance degraded but capacity remains.

### Alert Fatigue

Alert fatigue happens when alerts are noisy, unactionable, duplicated, or low-severity. Engineers stop trusting pages.

Fixes:

- Page only on actionable symptoms.
- Use severity levels.
- Add `for:` windows.
- Deduplicate alerts.
- Route warnings to ticket/chat, not pager.
- Include runbook links and useful labels.

### Good Alert Example

```text
CRITICAL: order-router 5xx rate > 2% for 5m
service=order-router env=prod route=/orders
current=4.8%
runbook=check deploy, dependency latency, exchange connectivity
```

Bad alert:

```text
CPU high
```

Better CPU alert:

```text
WARNING: order-router CPU > 85% for 20m and p95 latency > 200ms
```

### Incident Response

Alert should support:

- Severity.
- Affected service/environment.
- Start time.
- Current value and threshold.
- Links to dashboard/logs/runbook.
- Ownership/escalation.

## Interview Questions and Traps

- "Difference between metrics, logs, and traces?"
  - Answer: Metrics are numeric time-series, logs are event records, and traces follow one request across services.
- "What would you monitor for an order routing backend?"
  - Answer: Monitor traffic, p95/p99 latency, error/reject rate, queue depth/age, exchange connectivity, sequence gaps, stale data age, DB pool waits, and saturation.
- "What makes an alert actionable?"
  - Answer: It has impact, severity, owner, context, dashboard/log links, and a first response/runbook.
- "Why is high cardinality dangerous in Prometheus?"
  - Answer: It creates too many time series, increasing cost and making Prometheus queries/scrapes unreliable.
- "What is the difference between counter and gauge?"
  - Answer: A counter only increases and is used with rates; a gauge moves up/down for current state like queue depth or memory.
- "How do you calculate error rate?"
  - Answer: Failed requests divided by total requests over a time window, usually grouped by service/endpoint/status class.
- "Why should alerts have a `for` duration?"
  - Answer: It prevents paging on one-off blips and requires the condition to stay bad long enough to matter.

Trap: monitoring only CPU/memory. Strong answer includes application and business metrics.

## Performance and Reliability Considerations

- Avoid high-cardinality labels like raw `order_id`, `user_id`, or request path with IDs.
- Use histograms for latency, not just averages.
- Alert on symptoms first, causes second.
- Monitor saturation: CPU, memory, disk, file descriptors, queues, connection pools.
- Add deploy markers to dashboards.
- Make dashboards useful during incidents, not just for reporting.

## Common Mistakes

- Alerting on every exception without rate or impact.
- Using average latency instead of percentile latency.
- Missing queue depth/backlog metrics.
- No service ownership in alerts.
- No runbook link.
- Logging errors but not exposing error metrics.
- Using labels with unbounded values.

## Quick Revision

- Metrics detect and quantify, logs explain, traces localize distributed latency.
- Prometheus scrapes `/metrics`; Grafana visualizes; Alertmanager routes alerts.
- Counters increase, gauges move up/down, histograms model distributions.
- Good alerts are actionable, impact-based, deduplicated, and routed by severity.
- For backend/HFT, monitor latency, error rate, queues, exchange connectivity, feed lag, rejects, restarts, and saturation.
# Monitoring Prometheus Grafana and Alerting

Tags: #monitoring #prometheus #grafana #alerting #observability #backend #hft #interview

Use this note for production-oriented interview answers about monitoring backend systems that support trading operations.

Role bias: speak like someone who has debugged live services. Connect every metric, log, dashboard, and alert to user impact, trading risk, latency, availability, and recovery.

---

## Prometheus Basics

### Concept

Prometheus is a time-series monitoring system. Backend services expose numeric metrics over HTTP, usually at `/metrics`, and Prometheus periodically scrapes those endpoints.

Core ideas:

- **Metric**: numeric signal such as request count, latency bucket, queue depth, error count, active connections, reconnect count, or memory usage.
- **Label**: dimension attached to a metric, such as `service`, `endpoint`, `venue`, `status`, or `region`.
- **Time series**: one metric name plus one exact label set over time.
- **Scrape**: Prometheus pulls metrics from a target at a configured interval.
- **Exporter**: process that converts another system's state into Prometheus metrics.
- **PromQL**: query language used to aggregate, filter, and alert on time-series data.

Prometheus is usually not used for raw event logs. It is best for trends, rates, counters, gauges, histograms, and alertable conditions.

### Why It Matters In Backend Production

In a trading backend, the system can be "up" while still failing the business. Examples:

- Order API returns `200`, but p99 latency is too high during market open.
- Exchange connector is connected, but sequence gap count is increasing.
- Kafka consumer is alive, but lag is growing and risk updates are stale.
- Database is reachable, but connection pool wait time is causing order placement delays.

Prometheus helps answer: "What changed, when did it start, how bad is it, and which service/venue/endpoint is affected?"

### Pull Model

Prometheus uses a pull model:

```text
backend service exposes /metrics
        ^
        |
Prometheus scrapes every N seconds
        |
        v
time-series database + alert rules
```

Production relevance:

- Services do not need to know where Prometheus is.
- Prometheus controls scrape frequency and target health.
- Missing scrapes become a monitoring signal.
- Network/firewall rules must allow Prometheus to reach targets.

Common mistake: exposing `/metrics` only on localhost inside a container and then wondering why Prometheus cannot scrape it from outside the pod/container network.

### Scraping

A scrape target is an endpoint Prometheus polls.

Example scrape config:

```yaml
scrape_configs:
  - job_name: order-router
    scrape_interval: 5s
    static_configs:
      - targets:
          - order-router-1:9100
          - order-router-2:9100
```

Backend production example:

- `order-router` exposes request counters, latency histograms, exchange submission failures, and queue depth.
- Prometheus scrapes every `5s` because trading incidents need quick detection.
- Batch/reporting services may use `30s` or `60s` scrapes.

Tradeoff: very low scrape intervals increase monitoring load and metric volume. Use shorter intervals only for services where fast detection matters.

### Exporters

Exporters expose metrics for systems that do not natively speak Prometheus.

Common backend exporters:

- `node_exporter`: CPU, memory, disk, network, file descriptors.
- `postgres_exporter`: DB connections, locks, slow queries, replication lag.
- `redis_exporter`: memory, evictions, command latency.
- `kafka_exporter`: consumer lag, partition state.
- Custom exporter: exchange session status, FIX sequence gaps, order reject counts.

Production example:

An exchange gateway process writes FIX session state to an internal admin socket. A small exporter polls that socket and exposes:

```text
fix_session_up{venue="NASDAQ"} 1
fix_inbound_seq_gap_total{venue="NASDAQ"} 0
fix_reconnect_total{venue="NASDAQ"} 3
fix_heartbeat_lag_seconds{venue="NASDAQ"} 0.25
```

Interview point: exporters should be simple and reliable. A broken exporter can hide the actual service state.

### Metric Types

#### Counter

Monotonically increasing value. Use for totals.

Examples:

- `http_requests_total`
- `orders_submitted_total`
- `orders_rejected_total`
- `exchange_reconnects_total`

PromQL:

```promql
rate(http_requests_total{service="order-api"}[5m])
```

Use `rate()` or `increase()` on counters. Do not alert on the raw counter value.

#### Gauge

Value that can go up or down.

Examples:

- `queue_depth`
- `active_connections`
- `db_pool_in_use`
- `kafka_consumer_lag`
- `process_open_fds`

PromQL:

```promql
kafka_consumer_lag{consumer_group="risk-engine"} > 10000
```

#### Histogram

Samples observations into buckets. Best for latency distributions.

Examples:

- `http_request_duration_seconds_bucket`
- `exchange_submit_latency_seconds_bucket`
- `db_query_duration_seconds_bucket`

PromQL p99 latency:

```promql
histogram_quantile(
  0.99,
  sum by (le, endpoint) (
    rate(http_request_duration_seconds_bucket{service="order-api"}[5m])
  )
)
```

Common mistake: averaging latency hides tail latency. In HFT/backend interviews, mention p95/p99 and timeouts, not only averages.

### Labels And Cardinality

Labels make metrics useful, but high-cardinality labels can overload Prometheus.

Good labels:

- `service`
- `endpoint`
- `venue`
- `status_code`
- `region`
- `instance`

Dangerous labels:

- `order_id`
- `user_id`
- `request_id`
- raw exception message
- symbol/ticker if there are many thousands and high churn

Production failure example:

A developer adds `order_id` as a Prometheus label:

```text
order_submit_latency_seconds{order_id="A-9182371823"} 0.003
```

Every order creates a new time series. Prometheus memory spikes, queries slow down, dashboards time out, and monitoring becomes unreliable during the exact market window when it is needed.

Fix:

- Put high-cardinality identifiers in logs/traces.
- Keep metrics aggregated by stable operational dimensions.
- Use exemplars/traces if request-level linking is required.

### PromQL Basics

Useful patterns:

```promql
# Request rate by endpoint
sum by (endpoint) (
  rate(http_requests_total{service="order-api"}[5m])
)

# Error rate percentage
100 *
sum(rate(http_requests_total{service="order-api", status=~"5.."}[5m]))
/
sum(rate(http_requests_total{service="order-api"}[5m]))

# p99 API latency
histogram_quantile(
  0.99,
  sum by (le, endpoint) (
    rate(http_request_duration_seconds_bucket{service="order-api"}[5m])
  )
)

# Queue depth high for a specific venue
queue_depth{service="exchange-writer", venue="CME"} > 5000

# Missing scrape target
up{job="order-router"} == 0
```

PromQL interview traps:

- `rate()` needs a range vector like `[5m]`.
- `rate()` is for counters, not gauges.
- `histogram_quantile()` needs bucket metrics grouped by `le`.
- Missing data is not the same as zero.
- `sum()` without labels can hide which venue or endpoint is failing.

### Python Backend Metrics Example

Minimal FastAPI-style example:

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI, Response
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
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

ORDER_QUEUE_DEPTH = Gauge(
    "order_queue_depth",
    "Pending orders waiting for exchange submission",
    ["venue"],
)

@app.middleware("http")
async def observe_requests(request, call_next):
    start = time.perf_counter()
    endpoint = request.url.path
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        LATENCY.labels(endpoint=endpoint).observe(time.perf_counter() - start)
        REQUESTS.labels(endpoint=endpoint, method=request.method, status=status).inc()

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

Production considerations:

- Avoid per-request dynamic labels like full URL with IDs.
- Use route templates like `/orders/{id}` instead of `/orders/123`.
- Expose queue depth from the real queue, not a stale cached variable.
- Pick histogram buckets that match backend latency expectations.

### Alert Integration Basics

Prometheus evaluates alert rules. Alertmanager routes alerts to Slack, PagerDuty, email, or incident tooling.

Example alert rule:

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
        for: 10m
        labels:
          severity: critical
          service: order-api
        annotations:
          summary: "Order API 5xx rate above 2%"
          runbook: "Check recent deploys, DB pool saturation, exchange writer errors, and upstream timeouts."
```

Alerting best practice: alert on symptoms and user/business impact first, then use cause alerts as diagnostics.

---

## Grafana Basics

### Concept

Grafana visualizes metrics, logs, and traces from systems such as Prometheus, Loki, Elasticsearch, Tempo, Jaeger, and databases.

In production, Grafana is a debugging surface:

- dashboards show service health;
- panels reveal correlations;
- annotations mark deploys/incidents;
- variables filter by service, venue, instance, or region;
- links jump from metrics to logs/traces.

### Why It Matters In Backend Production

During an incident, engineers need fast answers:

- Is the issue global or one venue?
- Did it start after deploy?
- Are errors from our service, an upstream exchange, DB, Kafka, or network?
- Are retries helping or making load worse?
- Is failover required?

Grafana should reduce time-to-diagnosis. A dashboard that looks impressive but does not answer operational questions is not useful.

### Dashboard Structure For Backend Services

A strong backend service dashboard usually has:

- **Golden signals**: traffic, errors, latency, saturation.
- **Dependency panels**: DB latency, cache errors, Kafka lag, exchange session state.
- **Resource panels**: CPU, memory, GC, file descriptors, sockets.
- **Business/flow panels**: orders accepted, orders rejected, quote updates processed, reconciliation backlog.
- **Recent deploy annotations**.

Example order API dashboard:

```text
Row 1: request rate, 5xx rate, p95/p99 latency, timeout count
Row 2: order accepted/rejected rate, reject reason breakdown, venue routing failures
Row 3: DB pool usage, DB query p99, Redis latency, Kafka publish failures
Row 4: CPU, memory, open fds, network retransmits, pod restarts
Row 5: logs panel filtered by service="order-api" and severity>=error
```

### Common Dashboard Metrics

API/service:

- `rate(http_requests_total[5m])`
- error rate by status class
- p50/p95/p99 latency
- timeout count
- in-flight requests
- request/response payload size if relevant

Trading backend:

- order submission rate
- order reject rate by venue/reason
- exchange reconnect count
- FIX sequence gaps
- market data message rate
- queue depth by venue
- stale price/risk age
- reconciliation backlog

Infrastructure:

- CPU saturation
- memory usage and OOM kills
- disk space and inode usage
- network errors/retransmits
- file descriptor usage
- process restarts

Dependency:

- DB query latency
- DB pool wait time
- cache hit ratio and latency
- Kafka consumer lag
- upstream API latency and error rate

### Production Debugging Workflow In Grafana

Scenario: order placement latency spikes at market open.

Workflow:

1. Open order API dashboard for the incident window.
2. Check request rate: normal volume or sudden burst?
3. Check p99 latency by endpoint: all endpoints or `/orders` only?
4. Check 5xx/timeouts: latency-only or actual errors?
5. Check DB pool wait and query latency.
6. Check exchange writer queue depth by venue.
7. Check CPU, memory, GC, and file descriptors.
8. Use deploy annotations to rule in/out recent release.
9. Jump to logs for slow requests and dependency errors.

Good interview answer: "I would narrow blast radius first: service-wide vs endpoint-specific vs venue-specific vs instance-specific. Then I would correlate latency with saturation and dependency metrics."

### Grafana Mistakes

- Too many panels and no incident workflow.
- Only average latency, no p95/p99.
- No labels or variables to isolate venue/endpoint/instance.
- Dashboards depend on metrics with dangerous cardinality.
- Missing deploy annotations.
- No clear owner/runbook link.
- Alert panels show red but do not explain user impact.

### Quick Revision

- Grafana does not collect metrics by itself; it visualizes data sources.
- Good dashboards answer operational questions quickly.
- Backend dashboards should show traffic, errors, latency, saturation, dependencies, and business flow.
- In HFT/backend systems, include venue/session/queue/backlog metrics.
- Dashboards should support incident triage, not just executive reporting.

---

## Metrics Vs Logs

### Concept

Metrics are aggregated numeric signals over time. Logs are event records.

| Signal | Best For | Example |
|---|---|---|
| Metrics | alerting, trends, rates, dashboards | p99 latency, error rate, queue depth |
| Logs | explaining individual events | order rejected because venue timeout |
| Traces | following one request across services | API -> risk -> router -> exchange |

### When To Use Metrics

Use metrics when you need:

- alerting;
- trend detection;
- SLO tracking;
- capacity planning;
- service health dashboards;
- fast aggregation by label.

Examples:

- `order_rejects_total{venue="CME", reason="timeout"}`
- `exchange_session_up{venue="NASDAQ"}`
- `risk_snapshot_age_seconds`
- `db_pool_wait_seconds_bucket`

### When To Use Logs

Use logs when you need:

- request/order/session-level context;
- exception stack traces;
- exact input/output metadata;
- audit-style event history;
- debugging why one operation failed.

Example structured log:

```json
{
  "level": "ERROR",
  "service": "order-router",
  "event": "exchange_submit_failed",
  "venue": "CME",
  "order_id": "ord-98217",
  "client_order_id": "desk-a-104",
  "error": "submit timeout after 250ms",
  "latency_ms": 251,
  "request_id": "req-77a"
}
```

Put `order_id` and `request_id` in logs, not metric labels.

### Structured Logging Basics

Structured logs are machine-readable logs, usually JSON.

Production benefits:

- filter by `service`, `request_id`, `venue`, `order_id`;
- correlate logs across services;
- avoid fragile text parsing;
- support incident timelines;
- improve postmortems.

Python logging example:

```python
import logging

logger = logging.getLogger("order-router")

def submit_order(order, venue_client):
    try:
        venue_client.submit(order)
    except TimeoutError:
        logger.exception(
            "exchange_submit_failed",
            extra={
                "venue": order.venue,
                "order_id": order.order_id,
                "symbol": order.symbol,
                "timeout_ms": 250,
            },
        )
        raise
```

Production note: ensure your logging stack preserves `extra` fields as structured fields. Some plain formatters flatten them or drop them.

### Debugging Production Incidents

Scenario: API error rate spikes.

Use metrics first:

- detect spike and affected service;
- break down by endpoint/status/instance;
- check dependency latency and saturation;
- determine start time and blast radius.

Then use logs:

- inspect representative failing requests;
- group by error type;
- find request IDs/order IDs;
- check stack traces and upstream response codes.

Then use traces if available:

- find which span dominates latency;
- identify retries/timeouts;
- confirm cross-service propagation.

Interview phrase: "Metrics tell me that something is wrong and where to look; logs tell me what happened for specific requests; traces show the path and latency contribution across services."

### Common Mistakes

- Logging every request at high volume in a latency-sensitive service.
- Using logs as the only alerting source.
- Missing request IDs, venue, endpoint, or order IDs.
- Putting secrets, tokens, or full payloads in logs.
- Using unstructured text that cannot be searched reliably.
- Adding high-cardinality labels to metrics because logs are hard to query.
- No sampling strategy for noisy success logs.

### Quick Revision

- Metrics are for aggregate health and alerting.
- Logs are for event-level explanation.
- Traces are for request path and cross-service latency.
- Structured logs beat free-form strings in incidents.
- Do not put request/order IDs in Prometheus labels.

---

## Alerting Systems

### Concept

An alerting system detects conditions that require human or automated action.

Typical pipeline:

```text
service metrics/logs
    -> Prometheus / log backend
    -> alert rule
    -> Alertmanager
    -> route/deduplicate/silence
    -> Slack/PagerDuty/on-call
    -> incident workflow/runbook
```

Alerts are production contracts. A page should mean: "Someone must act now."

### Critical Vs Warning Alerts

Critical alerts:

- customer/trading impact now;
- service down or losing requests;
- sustained high error rate;
- exchange connectivity lost during trading hours;
- order queue growing and not draining;
- stale risk/position data.

Warning alerts:

- capacity risk soon;
- elevated latency but below user-impact threshold;
- disk space trending low;
- reconnect count increasing;
- one replica unhealthy but redundancy remains.

Production example:

```yaml
- alert: ExchangeSessionDown
  expr: exchange_session_up{venue="CME"} == 0
  for: 30s
  labels:
    severity: critical
  annotations:
    summary: "CME exchange session is down"
    action: "Check gateway logs, network route, heartbeat lag, and failover policy."
```

In HFT systems, thresholds may depend on market hours. A disconnected venue at 3 AM may be warning; during trading hours it may be critical.

### False Positives And Alert Fatigue

False positives train engineers to ignore alerts.

Common causes:

- threshold too low;
- no `for` duration;
- alerting on every instance instead of service impact;
- no maintenance windows;
- alerting on cause without impact;
- noisy warnings routed to pager;
- missing dependency suppression.

Fixes:

- add `for: 5m` or appropriate duration;
- alert on rate/percentage, not single event;
- group by service/venue;
- route warnings to Slack, critical to pager;
- include runbooks and dashboards;
- tune after incidents.

### Practical Alert Examples

High 5xx rate:

```yaml
- alert: ApiHigh5xxRate
  expr: |
    100 *
    sum(rate(http_requests_total{service="order-api",status=~"5.."}[5m]))
    /
    sum(rate(http_requests_total{service="order-api"}[5m]))
    > 1
  for: 5m
  labels:
    severity: critical
```

Queue not draining:

```yaml
- alert: ExchangeWriterQueueBacklog
  expr: |
    order_queue_depth{service="exchange-writer"} > 10000
    and
    rate(orders_sent_total{service="exchange-writer"}[5m]) < 10
  for: 2m
  labels:
    severity: critical
```

Stale market data:

```yaml
- alert: MarketDataStale
  expr: market_data_age_seconds{feed="primary"} > 1
  for: 15s
  labels:
    severity: critical
```

Instance down but service still redundant:

```yaml
- alert: OrderApiReplicaDown
  expr: up{job="order-api"} == 0
  for: 2m
  labels:
    severity: warning
```

### Incident Response Workflow

When paged:

1. Acknowledge the alert.
2. Confirm user/business impact.
3. Check dashboard linked in alert.
4. Narrow blast radius: service, endpoint, venue, region, instance.
5. Check recent deploy/config changes.
6. Look for saturation: CPU, memory, DB pool, queues, network.
7. Check logs around alert start time.
8. Mitigate first: rollback, failover, disable route, increase capacity, drain queue.
9. Communicate status.
10. After recovery, write a short postmortem and fix alert/runbook gaps.

Backend interview answer: "I separate mitigation from root cause. In a trading system, restoring safe operation comes before perfect explanation."

### Common Interview Questions And Traps

Questions:

- How do you design alerts for an order API?
  - Answer: Alert on symptoms: sustained high `5xx`, p99 latency, reject spikes, queue age, exchange disconnects, and stale order states.
- What is alert fatigue?
  - Answer: Noisy, unactionable, duplicate, low-severity pages without owners or runbooks.
- When should an alert page someone?
  - Answer: When there is current or imminent user/business impact that requires human action.
- How do you avoid false positives?
  - Answer: Use `for` durations, rate-based thresholds, deploy/maintenance awareness, severity levels, and multi-signal alerts.
- What should be included in an alert message?
  - Answer: Include service, environment, severity, current value, threshold, start time, affected scope, dashboard/log/runbook links, and owner.
- How do you alert on latency without paging on every small spike?
  - Answer: Use percentile histograms over windows, sustained conditions, traffic minimums, and impact thresholds instead of single-request spikes.

Traps:

- Saying "alert on CPU > 80%" as the main service alert.
- Ignoring business impact.
- No distinction between warning and critical.
- No `for` duration.
- No runbook/dashboard link.
- Alerting on raw counters instead of rates.

### Quick Revision

- Critical alerts require immediate action.
- Warning alerts indicate risk but should not wake someone by default.
- Alert on symptoms first: errors, latency, stale data, lost connectivity, undrained queues.
- Tune alerts continuously using incident feedback.
- Every page should have context, owner, dashboard, and first action.

