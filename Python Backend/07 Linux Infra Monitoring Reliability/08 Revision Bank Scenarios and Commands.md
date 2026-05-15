# Revision Bank Scenarios and Commands

Tags: #revision #interview-questions #incidents #debugging #prometheus #grafana #backend #hft

Use this file in the final hour before an interview. Keep answers practical: signal, output, interpretation, impact, mitigation.

## Answer Pattern

For Linux, monitoring, or reliability questions:

1. State the concept or command.
2. Explain what signal it gives.
3. Show the command/query/code.
4. Explain expected output.
5. Say how you would act safely.

Example:

```bash
systemctl status order-router
journalctl -u order-router --since "15 min ago" -p warning
ss -ltnp | grep ':8080'
curl -fsS --max-time 2 http://127.0.0.1:8080/ready
```

Expected output:

```text
Active: activating (auto-restart) (Result: exit-code)
OSError: [Errno 98] Address already in use
LISTEN 0 4096 0.0.0.0:8080 users:(("python",pid=9912,fd=12))
```

Interpretation: the service is restarting because another process already owns the port. Identify the owner before stopping anything.

## Top Interview Questions

### How would you monitor a backend order API?

Strong answer: monitor request rate, error rate, p95/p99 latency, queue depth/age, dependency latency, DB pool usage, exchange session state, order rejects, stale data, and process saturation. Break down by endpoint, venue, status, instance, and region.

Warning: CPU and memory are useful, but they are not enough. A trading outage can happen while CPU looks normal.

### What is Prometheus?

Prometheus is a time-series monitoring system. Services expose `/metrics`; Prometheus scrapes those endpoints; PromQL is used for dashboards and alert rules.

```promql
up{job="order-api"}
```

Expected output:

```text
up{job="order-api",instance="order-api-01:9000"} 1
up{job="order-api",instance="order-api-02:9000"} 0
```

Interpretation: one target is scrapeable and one is not. Next checks are target status, network, port, path, auth, and service logs.

### Metrics vs logs vs traces?

Metrics detect and quantify. Logs explain individual events. Traces show cross-service request flow.

```text
Metrics: p99 latency rose to 900ms
Logs: request_id=req-77 failed with exchange_timeout
Trace: API spent 780ms waiting for risk service
```

### What makes an alert useful?

A useful alert is actionable and tied to impact. It includes service, severity, scope, current value, threshold, owner, dashboard/log links, and a first action.

```yaml
- alert: OrderApiHigh5xxRate
  expr: |
    100 *
    sum(rate(http_requests_total{service="order-api",status=~"5.."}[5m]))
    /
    sum(rate(http_requests_total{service="order-api"}[5m]))
    > 2
  for: 5m
  labels:
    severity: critical
```

Justification: the rule pages on sustained error percentage, not one exception.

### How do you debug an API latency spike?

Check p99 by endpoint, traffic rate, error/timeout rate, instance split, dependency latency, queue depth, DB pool wait, CPU/memory, file descriptors, and recent deploys.

```bash
top -p "$(pgrep -f order-api | head -1)"
ss -tanp | grep order-api | awk '{print $1}' | sort | uniq -c
grep -E "timeout|latency_ms|ERROR" /var/log/order-api/app.log | tail -100
```

Example output:

```text
  420 SYN-SENT
  110 ESTAB
error=dependency_timeout dependency=risk latency_ms=1200
```

Interpretation: many outbound connection attempts plus risk timeouts suggest dependency/network pressure, not just local CPU.

### Liveness vs readiness?

Liveness decides whether to restart the process. Readiness decides whether to send traffic to the instance.

```text
/live -> process/event loop responsive
/ready -> DB/Kafka/risk state loaded enough to serve
```

Warning: keep liveness mostly local. Put dependency and stale-state checks in readiness or alerts.

### When are retries dangerous?

Retries are dangerous for overload, long outages, non-idempotent writes, missing deadlines, and unknown external side effects.

Trading example: if order submit times out, the exchange may still have accepted it. Use `client_order_id`, persist attempt state, query order status, and reconcile before resubmitting.

### What is a circuit breaker?

A circuit breaker stops calls to a failing dependency and fails fast for a cooldown period.

```text
Closed -> normal calls
Open -> fail fast / fallback
Half-open -> limited test calls
```

Justification: it protects caller threads, connection pools, and queues during dependency failure.

### What is graceful degradation?

Graceful degradation means preserving safe core behavior during partial failure. Examples: read-only mode, cached reference data, disable analytics writes, reject new orders while allowing safe cancels.

Warning: in trading systems, graceful degradation may mean fail closed. Do not accept risky work just to stay "available."

### SLA, SLO, SLI?

```text
SLI: measured signal
SLO: internal target
SLA: external commitment
```

Example:

```text
SLI: percentage of order submissions succeeding under 100ms
SLO: 99.9% during market hours
SLA: contractual client promise, if applicable
```

## Important Commands

### Process and Service

```bash
ps aux --sort=-%cpu | head
ps aux --sort=-%mem | head
pgrep -af order-router
top -p 1234
systemctl status order-router
systemctl cat order-router
journalctl -u order-router --since "30 min ago"
```

Expected output:

```text
PID  %CPU %MEM CMD
1234 92.1 12.4 python -m order_router
Active: active (running)
```

Interpretation: high CPU with active service means check traffic, logs, recent deploys, hot code paths, and saturation before restarting.

### Network and Ports

```bash
ss -ltnp
ss -tan | awk 'NR > 1 {print $1}' | sort | uniq -c | sort -nr
lsof -i :8080
curl -v --max-time 2 http://127.0.0.1:8080/health
```

Expected output:

```text
LISTEN 0 4096 0.0.0.0:8080 users:(("python",pid=1234,fd=12))
821 ESTAB
142 TIME-WAIT
23 SYN-SENT
```

Interpretation: the service listens on `8080`; many `SYN-SENT` connections suggest blocked or unreachable outbound dependencies.

### Logs and Text Processing

```bash
grep -n "ERROR" app.log
grep -C 3 "order_id=ORD-42" app.log
zgrep "timeout" app.log.1.gz
awk '{print $1}' access.log | sort | uniq -c | sort -nr | head
sed -n '100,140p' app.log
```

Expected output:

```text
381 exchange_timeout
27 validation_error
8 auth_rejected
```

Interpretation: most failures are dependency timeouts, not invalid client input.

### Host Pressure

```bash
free -h
vmstat 1 5
df -h
du -sh /var/log/*
lsof | grep deleted
dmesg -T | grep -i "killed process"
```

Expected output:

```text
Out of memory: Killed process 1234 (python)
/var/log/order-router/app.log (deleted)
```

Interpretation: the process may have been OOM-killed, and disk may remain full if a running process still holds a deleted file.

### Docker

```bash
docker ps
docker ps -a
docker logs --tail 100 order-router
docker port order-router
docker exec order-router ss -ltnp
docker inspect order-router
docker stats
```

Expected output:

```text
0.0.0.0:8080->8080/tcp
LISTEN 0 4096 127.0.0.1:8080
```

Interpretation: the host port is published, but the app inside the container may be bound to localhost. Bind to `0.0.0.0` inside the container.

## Common Scenarios

### Service Down After Deploy

```bash
systemctl status order-router
journalctl -u order-router --since "15 min ago" -n 200
systemctl cat order-router
ls -l /etc/order-router.env
ss -ltnp | grep 8080
```

Look for config errors, missing environment variables, permission denied, port conflicts, dependency startup failure, or crash loops.

Fix pattern: confirm impact, roll back if severe, fix config/permissions, restart one instance first if possible, and verify readiness plus metrics.

### Orders Rejected Suddenly

```bash
grep "order_rejected" app.log \
  | awk -F'reason=' '{print $2}' \
  | awk '{print $1}' \
  | sort | uniq -c | sort -nr
```

Expected output:

```text
182 risk_limit
47 invalid_symbol
9 exchange_closed
```

Interpretation: `risk_limit` suggests risk config/account state; `invalid_symbol` suggests reference data or client input; `exchange_closed` suggests calendar/schedule issue.

### Disk Full

```bash
df -h
du -sh /var/log/* | sort -h
lsof | grep deleted
```

Fix: rotate or compress logs, restart/reopen the process holding deleted files only after checking impact, add retention, and alert before disk becomes critical.

### Cron Job Fails Under Cron

```bash
crontab -l
journalctl -u cron --since today
ls -l /opt/scripts/job.sh
env -i /bin/bash -lc '/opt/scripts/job.sh'
```

Expected output:

```text
/bin/sh: 1: python: not found
```

Interpretation: cron has a minimal environment. Use full paths, set environment explicitly, redirect logs, and prevent overlap with `flock`.

## Reliability Fix Patterns

Missing timeout:

```python
requests.get(url, timeout=(0.2, 1.0))
```

Justification: the connect timeout protects setup; the read timeout protects waiting for response bytes.

Retry storm:

```text
dependency slows -> clients retry -> load multiplies -> dependency slows more
```

Fix with bounded retries, backoff, jitter, deadlines, retry budgets, circuit breakers, and idempotency.

Unbounded queue:

```text
downstream slows -> queue grows -> memory grows -> process OOMs
```

Fix with queue bounds, backpressure, load shedding, and queue depth/age alerts.

## Final One-Hour Revision Plan

1. Review `ps`, `top`, `ss`, `lsof`, `systemctl`, and `journalctl`.
2. Practice `grep`, `awk`, and `sed` on sample logs.
3. Memorize liveness vs readiness.
4. Memorize counter vs gauge vs histogram.
5. Practice explaining retry danger with duplicate orders.
6. Review Docker debugging commands.
7. Practice one incident answer: latency spike, crashed service, rejected orders, disk full.
8. Keep answers practical: command, output, interpretation, safe fix.
