# Revision Bank Scenarios and Commands

Tags: #revision #interview-questions #incidents #debugging #prometheus #grafana #backend #hft

Fast revision bank for reliability, monitoring, observability, production debugging, and HFT/backend systems interviews.

Use this file in the final hour before an interview. Keep answers practical: signal, impact, diagnosis, mitigation, tradeoff.

---

## Top 25 Reliability And Monitoring Interview Questions

### 1. How would you monitor a backend order API?

Strong answer:

- Track traffic, error rate, p95/p99 latency, saturation, dependency latency, DB pool usage, queue depth, and order rejects.
- Break down by endpoint, venue, status code, instance, and region.
- Add structured logs with request ID and order ID.
- Alert on sustained user-impacting error/latency, not only CPU.

Trap: only mentioning CPU/memory dashboards.

### 2. What is Prometheus and how does it collect metrics?

Strong answer:

- Prometheus stores time-series metrics.
- Services expose `/metrics`.
- Prometheus scrapes targets using a pull model.
- PromQL is used for queries and alert rules.
- Exporters expose metrics for systems like Linux, Postgres, Kafka, Redis, or custom exchange gateways.

Trap: saying applications push logs to Prometheus.

### 3. What is the difference between metrics and logs?

Strong answer:

- Metrics are numeric aggregate signals for alerting and trends.
- Logs are event-level records for explaining specific failures.
- Traces show request flow across services.
- Use metrics to detect, logs/traces to investigate.

Trap: storing request IDs as metric labels.

### 4. How do you design useful alerts?

Strong answer:

- Alert on symptoms: high error rate, high p99 latency, stale data, lost exchange session, undrained queues.
- Use severity, duration, grouping, deduplication, runbook links, and dashboard links.
- Critical alerts should require immediate action.
- Warnings should not page unless they predict imminent impact.

Trap: paging on every single exception.

### 5. What causes alert fatigue?

Strong answer:

- Too many noisy, unactionable, low-priority alerts.
- No distinction between warning and critical.
- Alerts without owners, runbooks, or context.
- Thresholds that do not map to user impact.

Fix:

- tune thresholds;
- add `for` duration;
- group alerts;
- route warnings differently;
- delete unactionable alerts.

### 6. How do you debug an API latency spike?

Strong answer:

1. Check traffic increase and p99 by endpoint.
2. Check error rate and timeout count.
3. Break down by instance/region/venue.
4. Check dependencies: DB, cache, Kafka, upstream APIs.
5. Check saturation: CPU, memory, threads, connection pools, queues.
6. Check recent deploys/config changes.
7. Use logs/traces for slow requests.

Trap: immediately restarting the service without diagnosis or impact assessment.

### 7. What is a health check?

Strong answer:

- A health check exposes service state.
- Liveness decides whether the process should be restarted.
- Readiness decides whether the instance should receive traffic.
- Dependency health should be used carefully.

Trap: liveness checks every downstream dependency and causes restart storms.

### 8. Liveness vs readiness?

Strong answer:

- Liveness: "is this process stuck and should it be restarted?"
- Readiness: "can this instance safely serve traffic?"
- Liveness should be local and cheap.
- Readiness can include critical dependencies and stale state.

### 9. What is an SLO?

Strong answer:

- SLO is an internal reliability target.
- It is measured using SLIs.
- Example: 99.9% of order submissions succeed under 100ms during trading hours.

Trap: saying SLO is just "server uptime."

### 10. How would you monitor exchange connectivity?

Strong answer:

- FIX session up/down.
- heartbeat lag.
- reconnect count.
- sequence gap count.
- logout/reject messages.
- order ack latency.
- per-venue queue depth.
- stale market data age.

Trap: only pinging the exchange IP.

### 11. What is a retry storm?

Strong answer:

- Many clients retry a degraded dependency and amplify load.
- It causes worse latency, saturation, and cascading failure.
- Prevent with bounded retries, backoff, jitter, deadlines, retry budgets, circuit breakers, and bulkheads.

### 12. When should you not retry?

Strong answer:

- Invalid request.
- Auth failure.
- Risk rejection.
- Non-idempotent write without deduplication.
- Long-running operation whose result is unknown.

Trading example: never blindly retry an order submit if you do not know whether the exchange accepted it.

### 13. What is idempotency and why does it matter?

Strong answer:

- Repeating an operation has the same effect as doing it once.
- Required for safe retries of writes.
- Use client order IDs, request IDs, deduplication tables, and reconciliation.

### 14. What is a circuit breaker?

Strong answer:

- A resilience pattern that stops calls to a failing dependency.
- Closed: normal calls.
- Open: fail fast or fallback.
- Half-open: limited test calls.
- Prevents cascading failure and preserves caller resources.

### 15. How do you choose between fail-open and fail-closed?

Strong answer:

- Depends on business safety.
- For risk checks/order validation, fail closed.
- For non-critical enrichment or analytics, fail open/degrade.
- In trading systems, correctness and risk control often beat availability.

### 16. What is graceful degradation?

Strong answer:

- Continue reduced safe functionality during partial failure.
- Examples: read-only mode, cached reference data, reject new orders but allow cancels, disable analytics writes.

Trap: assuming graceful degradation means "serve stale or unsafe data."

### 17. What metrics would you put on a Grafana dashboard?

Strong answer:

- traffic, errors, latency, saturation;
- dependency health and latency;
- queue depth and consumer lag;
- business metrics such as orders accepted/rejected;
- per-venue session status;
- deploy annotations.

### 18. What is high cardinality in Prometheus?

Strong answer:

- Too many unique label combinations.
- Dangerous labels include order ID, user ID, request ID, raw URL, exception string.
- It increases memory, query cost, and monitoring instability.

### 19. How do you alert on latency?

Strong answer:

- Use histogram buckets and `histogram_quantile`.
- Alert on sustained p95/p99 above SLO.
- Scope by endpoint/service/venue.
- Pair with traffic threshold to avoid low-volume noise.

### 20. How do you debug missing Prometheus metrics?

Strong answer:

- Check `/metrics` endpoint manually.
- Check Prometheus target page and `up` metric.
- Verify scrape config, service discovery, network/firewall, auth, endpoint path, and port.
- Check metric name/label changes.

### 21. How do you debug a service that is up but not working?

Strong answer:

- Check readiness and functional checks.
- Check dependency health.
- Check logs for business errors.
- Check queues/backlogs.
- Check stale state metrics.
- Confirm with synthetic transaction.

### 22. How do you handle a production incident?

Strong answer:

- Acknowledge and assess impact.
- Narrow blast radius.
- Mitigate first.
- Communicate.
- Verify recovery.
- Write postmortem and fix prevention/detection gaps.

### 23. What is backpressure?

Strong answer:

- Mechanism to slow/reject work when downstream cannot keep up.
- Examples: bounded queues, rate limits, `429/503`, pausing consumers, load shedding.
- Prevents unbounded memory growth and latency collapse.

### 24. What is fault isolation?

Strong answer:

- Preventing one failing component from consuming shared resources or taking down healthy paths.
- Examples: per-venue queues, separate thread pools, dependency-specific connection pools, circuit breakers.

### 25. What production mistakes have you seen or would you avoid?

Strong answer:

- No timeouts.
- Infinite retries.
- High-cardinality metrics.
- Health checks that always return `200`.
- Alerting only on CPU.
- No request IDs in logs.
- No dashboards for business flows.
- Restarting during trading hours without understanding state/failover.

---

## Most Important Observability Concepts To Revise

Golden signals:

- **Traffic**: request rate, order rate, message rate.
- **Errors**: 5xx, rejects, timeouts, reconnect failures.
- **Latency**: p95/p99, dependency latency, end-to-end order ack latency.
- **Saturation**: CPU, memory, thread pools, DB pools, queue depth, file descriptors.

Backend-specific signals:

- DB query latency and pool wait.
- Kafka consumer lag.
- Redis latency/evictions.
- exchange session state.
- FIX sequence gaps.
- stale data age.
- order queue depth.
- reconciliation backlog.

Operational concepts:

- symptoms vs causes;
- SLIs/SLOs;
- high-cardinality labels;
- structured logging;
- correlation IDs;
- distributed tracing;
- alert severity;
- runbooks;
- deployment annotations;
- synthetic monitoring.

Quick mental model:

```text
Metrics: Is something wrong? Where? How bad?
Logs: What happened in specific events?
Traces: Where did one request spend time?
Dashboards: Can I triage quickly?
Alerts: Does a human need to act now?
```

---

## Common Production Outages And Debugging Approaches

### Outage: Service Returns 5xx

Likely causes:

- bad deploy;
- DB unavailable;
- config/secrets issue;
- dependency timeout;
- unhandled exception;
- resource exhaustion.

Debug:

```bash
systemctl status order-api
journalctl -u order-api --since "15 min ago" -p warning
ss -tanp | grep ':443'
```

Metrics:

- `rate(http_requests_total{status=~"5.."}[5m])`
- DB pool usage;
- dependency error rate;
- pod/container restarts.

Fix:

- rollback;
- restore config/secret;
- fail over dependency;
- shed load;
- patch exception after mitigation.

### Outage: Latency Spike Without Errors

Likely causes:

- slow dependency;
- DB locks;
- queue buildup;
- GC/memory pressure;
- thread pool saturation;
- network retransmits;
- noisy neighbor.

Debug:

- compare p50 vs p99;
- split by endpoint/instance;
- check dependency dashboards;
- inspect slow logs/traces;
- check queue depth and pool wait.

Fix:

- rollback slow code path;
- reduce concurrency;
- add backpressure;
- tune query/index;
- increase capacity only if bottleneck supports it.

### Outage: Queue Backlog

Likely causes:

- consumers down;
- downstream slow;
- partition imbalance;
- poison message;
- rate spike;
- lock contention.

Debug:

- queue depth by partition/venue;
- consumer lag;
- processing rate vs incoming rate;
- error logs for poison messages;
- downstream latency.

Fix:

- pause bad partition/message;
- scale consumers if downstream can handle it;
- fix poison message handling;
- shed low-priority input;
- replay after recovery.

### Outage: Exchange Session Down

Likely causes:

- network route issue;
- exchange outage;
- heartbeat timeout;
- bad credentials/session conflict;
- sequence number mismatch;
- gateway deploy/config issue.

Debug:

- session state metric;
- heartbeat lag;
- gateway logs;
- network connectivity;
- recent deploy/config;
- duplicate session on standby.

Fix:

- stop unsafe routing;
- reconnect if safe;
- fail over with split-brain protection;
- request sequence resend;
- reconcile open orders.

### Outage: Monitoring Blind Spot

Symptoms:

- user reports issue before alert;
- dashboard missing key metric;
- alert did not fire;
- Prometheus scrape target down.

Debug:

- check `up`;
- check scrape config;
- check missing label/name changes;
- check alert `for` window;
- check Alertmanager route/silence;
- check dashboard query.

Fix:

- add missing SLI;
- tune alert;
- add synthetic monitor;
- add runbook;
- test alert path.

---

## Common Backend Reliability Failures And Fixes

| Failure | Why It Hurts | Fix |
|---|---|---|
| No timeouts | requests hang and resources pile up | set connect/read/overall deadlines |
| Infinite retries | dependency overload | bounded retries with backoff/jitter |
| Retry writes blindly | duplicates or inconsistent state | idempotency keys and reconciliation |
| Shared worker pool | one dependency blocks all traffic | bulkheads and per-dependency pools |
| Unbounded queue | memory growth and stale work | bounded queue and backpressure |
| Health check always `200` | bad instances receive traffic | real readiness checks |
| Liveness checks DB | restart storm during DB blip | keep liveness local |
| Metrics with order ID labels | Prometheus overload | put IDs in logs/traces |
| Alert on CPU only | misses business outage | alert on error/latency/staleness/queues |
| No request IDs | slow incident debugging | correlation IDs in logs/traces |
| Cache as source of truth | stale/wrong data after failure | authoritative store and invalidation |
| Untested failover | recovery action causes new outage | regular failover drills |

---

## Practical Monitoring And Debugging Workflows

### Workflow: New Alert Fires

1. Read alert summary, service, severity, and runbook.
2. Open dashboard for the exact incident time window.
3. Confirm business impact.
4. Check if issue is global or scoped.
5. Check recent deploys/config changes.
6. Check golden signals.
7. Check dependency panels.
8. Inspect logs/traces for representative failures.
9. Mitigate.
10. Verify recovery and close the loop.

### Workflow: User Reports "Orders Are Slow"

1. Check order API p95/p99 latency.
2. Break down by endpoint and venue.
3. Check order ack latency from exchange gateway.
4. Check risk service latency.
5. Check DB pool wait and query latency.
6. Check exchange writer queue depth.
7. Check logs for timeout/retry patterns.
8. Verify whether issue affects new orders, cancels, or all operations.

### Workflow: Service Is Up But Not Processing

1. Check process/container status.
2. Check readiness endpoint.
3. Check worker heartbeat metric.
4. Check input queue depth and output rate.
5. Check dependency connectivity.
6. Check deadlocks/thread dumps if available.
7. Check logs for poison messages or stuck offsets.

### Workflow: Prometheus Alert Did Not Fire

1. Query the metric manually.
2. Check labels match alert expression.
3. Check `up` for scrape target.
4. Check alert rule syntax and evaluation.
5. Check `for` duration.
6. Check Alertmanager silences/routes.
7. Add a synthetic or more direct SLI if the metric was wrong.

---

## Quick Prometheus Revision

Metric types:

- Counter: monotonically increasing totals.
- Gauge: current value that can go up/down.
- Histogram: latency/size distribution with buckets.
- Summary: client-side quantiles, less flexible for aggregation.

Must-know PromQL:

```promql
# request rate
sum by (endpoint) (rate(http_requests_total[5m]))

# error percentage
100 * sum(rate(http_requests_total{status=~"5.."}[5m]))
/
sum(rate(http_requests_total[5m]))

# p99 latency
histogram_quantile(
  0.99,
  sum by (le, endpoint) (rate(http_request_duration_seconds_bucket[5m]))
)

# queue high
order_queue_depth{venue="NASDAQ"} > 5000

# scrape target down
up{job="order-api"} == 0
```

Rules:

- Use `rate()` for counters.
- Use gauges directly.
- Use histograms for p95/p99.
- Avoid high-cardinality labels.
- Missing data is not zero.
- Always include labels that help isolate blast radius.

---

## Quick Grafana Revision

Grafana is for visualization and incident triage.

Strong dashboard:

- starts with service-level health;
- has endpoint/venue/instance filters;
- shows p95/p99, not only averages;
- includes dependency panels;
- includes business flow panels;
- includes deploy annotations;
- links to logs/traces/runbook.

Bad dashboard:

- too many panels;
- no owner;
- no alert links;
- no business impact;
- only CPU/memory;
- cannot isolate incident scope.

Interview phrase:

"A good Grafana dashboard should let me go from alert to blast radius to likely bottleneck in a few minutes."

---

## Real-World Backend Incident Scenarios

### Scenario 1: Risk Service Timeout During Market Open

Symptoms:

- order API p99 latency > 500ms;
- risk timeout count spikes;
- order submission errors increase;
- retry count triples.

What to say:

- confirm impact and scope;
- check risk service saturation;
- reduce retries/open circuit breaker;
- fail closed for new orders if risk unavailable;
- allow safe cancels if supported;
- rollback if deploy caused it;
- add retry budget and dashboard panel after incident.

### Scenario 2: One Venue Queue Explodes

Symptoms:

- `order_queue_depth{venue="CME"}` grows;
- other venues normal;
- exchange writer threads saturated.

What to say:

- isolate per-venue impact;
- stop CME routing if unsafe;
- ensure one venue does not consume global worker pool;
- inspect CME session logs and ack latency;
- reconcile outstanding orders;
- add per-venue bulkheads if missing.

### Scenario 3: Prometheus Overloaded By Bad Label

Symptoms:

- Prometheus memory high;
- dashboard queries slow;
- new metric has `order_id` label;
- high time-series churn.

What to say:

- remove high-cardinality label;
- move ID to logs/traces;
- aggregate metrics by stable dimensions;
- reload/redeploy;
- add metric review in code review.

### Scenario 4: Readiness Check Lets Bad Pods Receive Traffic

Symptoms:

- some instances return 500;
- load balancer still routes to them;
- readiness only checks HTTP server.

What to say:

- add readiness checks for required initialized state;
- include DB/risk/Kafka only if hard dependencies;
- keep checks fast and side-effect free;
- use metrics to alert on readiness failures.

### Scenario 5: Health Check Causes Restart Storm

Symptoms:

- DB blip;
- all pods restart;
- outage lasts longer than DB issue;
- liveness checks query DB.

What to say:

- remove remote dependencies from liveness;
- move dependency checks to readiness;
- add startup probe if initialization is slow;
- tune failure thresholds.

### Scenario 6: Duplicate Order Risk After Timeout

Symptoms:

- order submit times out;
- client retries;
- exchange may have accepted original order;
- duplicate order possible.

What to say:

- use client order ID/idempotency key;
- persist submission state;
- check exchange state before resubmit;
- reconcile ambiguous outcomes;
- never blindly retry side-effecting order operations.

---

## HFT Backend Reliability Engineering Tips

- Treat latency spikes as reliability issues, not just performance issues.
- Monitor tail latency and stale data age.
- Separate per-venue resources to prevent one venue from hurting all venues.
- Prefer fail-closed for risk, order validation, and unknown exchange state.
- Make retries explicit, bounded, observable, and idempotent.
- Keep health checks cheap and operationally meaningful.
- Avoid restarts during market hours unless you understand state and failover.
- Always reconcile external state after reconnects, timeouts, and failovers.
- Alert on trading impact: lost session, stale market data, rejected orders, queue backlog.
- Keep runbooks short and executable under pressure.
- Add deploy annotations to dashboards.
- Test failover and recovery paths before relying on them.
- Use structured logs with request ID, order ID, venue, symbol, and error category.
- Be careful with average latency; p99 matters more for user-impacting workflows.
- Design dashboards around incident questions, not tool features.

---

## Final One-Page Revision

Reliability answer pattern:

1. Define the failure mode.
2. Explain user/trading impact.
3. Say what metric/log/trace reveals it.
4. Narrow blast radius.
5. Mitigate safely.
6. Mention prevention: timeout, retry, circuit breaker, health check, alert, dashboard, runbook.

Best interview phrases:

- "I would first confirm impact and blast radius."
- "Metrics tell me where to look; logs explain specific failures."
- "I would avoid blindly retrying non-idempotent order operations."
- "Liveness should be local; readiness determines traffic safety."
- "In trading systems, safe degradation may mean rejecting new orders."
- "A useful alert is actionable and tied to user or business impact."

# Revision Bank Scenarios and Commands

Tags: #revision #interview-questions #linux-commands #docker #debugging #hft

## Top 30 Linux Infra Monitoring Interview Questions

1. How would you debug a backend service that is running but not responding?
   - Answer: Confirm impact, check service status/logs, verify listening ports, test locally with `curl`, inspect CPU/memory/file descriptors, and check dependencies/recent deploys.
2. How do you find which process is using a port?
   - Answer: Use `ss -ltnp`, `lsof -i :PORT`, or `fuser PORT/tcp`, then map PID to command and service owner.
3. What is the difference between `ps`, `top`, `systemctl`, and `journalctl`?
   - Answer: `ps` shows process snapshots, `top` shows live resource pressure, `systemctl` manages services, and `journalctl` reads systemd logs.
4. What does `CLOSE-WAIT` mean, and why does it matter?
   - Answer: `CLOSE-WAIT` means the remote side closed and the local app has not closed its socket, often indicating leaked connections or stuck request cleanup.
5. How do you debug high CPU on a Python backend service?
   - Answer: Check `top`, per-PID CPU, logs, traffic, recent deploys, profiling, hot loops, serialization/compression, GC, and thread/process behavior.
6. How do you debug high memory usage or an OOM kill?
   - Answer: Check `free`, `top`, cgroup/container limits, `dmesg` OOM logs, queue depth, object growth, traffic spikes, leaks, and recent config/deploy changes.
7. Why can disk stay full after deleting a large log file?
   - Answer: A deleted file can still consume disk if a process holds it open; use `lsof | grep deleted` and restart/reopen logs safely.
8. What is a zombie process?
   - Answer: A zombie is an exited child process whose parent has not collected its exit status.
9. How do Linux file permissions work?
   - Answer: Linux permissions use owner/group/other bits for read, write, and execute, plus ownership and sometimes ACLs/special bits.
10. Why is `chmod 777` dangerous?
    - Answer: It lets everyone read/write/execute, enabling accidental modification, privilege abuse, and security exposure.
11. How do environment variables reach a backend process?
    - Answer: Env vars come from shell, service manager, container runtime, deployment config, or systemd unit files and are inherited by child processes.
12. Why can a cron job work manually but fail under cron?
    - Answer: Cron has a minimal environment, different working directory/path/user, no interactive shell, and different permissions/secrets.
13. How would you parse logs to count error reasons?
    - Answer: Filter by time/service, extract structured fields with `jq` or text with `awk`, then `sort | uniq -c | sort -nr`.
14. How do you trace a single request/order through logs?
    - Answer: Use request/order/correlation IDs across API, workers, queues, connector, and exchange logs with timestamps and service names.
15. What is the difference between metrics, logs, and traces?
    - Answer: Metrics quantify aggregate state, logs explain individual events, and traces show cross-service request flow/timing.
16. What metrics would you expose for an order routing backend?
    - Answer: Expose request rate, error/reject rate, p95/p99 latency, queue depth/age, exchange session state, sequence gaps, stale data age, and saturation.
17. What is the difference between a Prometheus counter, gauge, and histogram?
    - Answer: Counters increase, gauges move up/down, and histograms bucket observations for latency/size percentiles.
18. Why are high-cardinality labels dangerous?
    - Answer: High-cardinality labels create huge numbers of time series, increasing memory, storage, query cost, and scrape instability.
19. What makes an alert actionable?
    - Answer: It has impact, severity, owner, scope, current value, threshold, dashboard/log links, and a first response.
20. How do you reduce alert fatigue?
    - Answer: Delete unactionable alerts, add `for` durations, group/dedupe, route by severity, and tune from incident review.
21. What is the difference between liveness and readiness?
    - Answer: Liveness answers "restart this process?"; readiness answers "send traffic to this instance?"
22. When are retries dangerous?
    - Answer: During overload, long outages, non-idempotent writes, missing deadlines, and unknown external side effects.
23. How do you prevent duplicate order submission after timeout?
    - Answer: Use idempotency keys/client order IDs, persist intent before submit, replay prior responses, and reconcile with exchange before resubmitting.
24. What is a circuit breaker?
    - Answer: A circuit breaker stops calls to a failing dependency, fails fast temporarily, and probes recovery before reopening traffic.
25. How do you debug a production outage step by step?
    - Answer: Confirm impact, narrow blast radius, check metrics/logs/recent changes, mitigate safely, communicate, then root-cause and prevent recurrence.
26. What is graceful degradation?
    - Answer: It keeps core safety available by disabling noncritical features, using read-only/cached modes, rate limiting, or rejecting risky work.
27. What is the difference between SLA, SLO, and SLI?
    - Answer: SLA is the external commitment, SLO is the internal target, and SLI is the measured reliability signal.
28. Why can a Docker container run but still be unreachable?
    - Answer: The app may bind to localhost, the port may not be published, health checks may fail, firewall/network policy may block it, or dependencies may be unreachable.
29. What should not be stored in a Docker image?
    - Answer: Do not store secrets, private keys, production credentials, customer data, or environment-specific mutable config in images.
30. How does Ansible help reduce infrastructure drift?
    - Answer: Ansible keeps desired host state in versioned playbooks and applies it repeatedly/idempotently across hosts, reducing manual snowflake changes.

## Most Important Linux Commands to Revise

### Process and Service

```bash
ps aux
ps aux --sort=-%cpu | head
ps aux --sort=-%mem | head
pgrep -af order-router
top
top -p 1234
systemctl status order-router
systemctl cat order-router
sudo systemctl restart order-router
journalctl -u order-router --since "30 min ago"
journalctl -u order-router -f
```

### Network and Ports

```bash
ss -ltnp
ss -tanp
ss -tan | awk 'NR > 1 {print $1}' | sort | uniq -c | sort -nr
lsof -i :8080
lsof -Pan -p 1234 -i
curl -v --max-time 2 http://127.0.0.1:8080/health
```

### Files, Disk, and Permissions

```bash
ls -l
chmod 750 script.sh
chmod 600 ~/.ssh/id_ed25519
chown app:app file
df -h
du -sh /var/log/*
lsof | grep deleted
```

### Logs and Text Processing

```bash
tail -n 100 app.log
tail -f app.log
grep -n "ERROR" app.log
grep -C 3 "order_id=ORD-42" app.log
grep -R "request_id=req-11" /var/log/order-router/
zgrep "timeout" app.log.1.gz
awk '{print $1}' access.log | sort | uniq -c | sort -nr | head
sed -n '100,140p' app.log
```

### Host Pressure

```bash
free -h
vmstat 1 5
uptime
dmesg -T | grep -i "killed process"
```

### SSH and Copy

```bash
ssh app@prod-host
ssh -i ~/.ssh/prod_ed25519 app@prod-host
ssh -vvv app@prod-host
scp app@prod-host:/var/log/order-router/app.log .
rsync -avz app@prod-host:/var/log/order-router/ ./logs/
```

## Common Production Debugging Scenarios

### Service Down After Deploy

Commands:

```bash
systemctl status order-router
journalctl -u order-router --since "15 min ago" -n 200
systemctl cat order-router
ls -l /etc/order-router.env
ss -ltnp | grep 8080
```

Look for:

- Config error.
- Missing environment variable.
- Permission denied.
- Port conflict.
- Dependency unavailable.
- Crash loop.

Fix pattern:

- Confirm impact.
- Roll back if severe.
- Fix config/permissions.
- Restart one instance first.
- Verify readiness and metrics.

### API Latency Spike

Commands:

```bash
top -p "$(pgrep -f order-router | head -1)"
ss -tanp | grep order-router | awk '{print $1}' | sort | uniq -c
grep -E "timeout|latency_ms|ERROR" /var/log/order-router/app.log | tail -100
```

Check:

- Traffic spike.
- Queue depth.
- CPU/memory/swap.
- Dependency latency.
- Connection pool saturation.
- Recent deploy.

### Orders Rejected Suddenly

Commands:

```bash
grep "order_rejected" app.log | tail -100
grep "order_rejected" app.log \
  | awk -F'reason=' '{print $2}' \
  | awk '{print $1}' \
  | sort | uniq -c | sort -nr
```

Interpretation:

- `risk_limit`: risk config or account state.
- `invalid_symbol`: bad reference data or client input.
- `exchange_closed`: schedule/calendar issue.
- `exchange_timeout`: dependency/connectivity issue.

### Disk Full

Commands:

```bash
df -h
du -sh /var/log/* | sort -h
lsof | grep deleted
```

Fix:

- Rotate/compress logs.
- Restart process holding deleted files if safe.
- Add log retention.
- Alert before disk reaches critical level.

### Cron Job Did Not Run Correctly

Commands:

```bash
crontab -l
journalctl -u cron --since today
ls -l /opt/scripts/job.sh
env -i /bin/bash -lc '/opt/scripts/job.sh'
```

Fix:

- Use full paths.
- Set environment explicitly.
- Redirect logs.
- Prevent overlap with `flock`.

### Docker Container Unreachable

Commands:

```bash
docker ps
docker logs --tail 100 order-router
docker port order-router
docker exec order-router ss -ltnp
docker inspect order-router
```

Likely causes:

- Port not published.
- App listening on `127.0.0.1` inside container.
- Wrong port mapping.
- Health check failing.
- Host firewall/security group.

## Common Backend Reliability Failures and Fixes

### Missing Timeouts

Failure:

```text
Requests hang, workers saturate, latency climbs.
```

Fix:

```python
requests.get(url, timeout=(0.2, 1.0))  # connect timeout, read timeout
```

### Retry Storm

Failure:

```text
Dependency slows down, clients retry, service retries, load multiplies.
```

Fix:

- Exponential backoff.
- Jitter.
- Retry budget.
- Circuit breaker.
- Idempotency keys.

### Duplicate Order Risk

Failure:

```text
Client times out after sending order, retries, exchange receives duplicate.
```

Fix:

- Client order ID.
- Idempotency key.
- Query order state before resubmitting.
- Treat unknown execution state carefully.

### Unbounded Queue

Failure:

```text
Queue grows during dependency outage, memory increases, process OOMs.
```

Fix:

- Bound queue.
- Apply backpressure.
- Drop/degrade non-critical work.
- Alert on queue depth and age.

### Bad Alerting

Failure:

```text
Pager fires for non-actionable warnings, real incidents get ignored.
```

Fix:

- Page on symptoms/user impact.
- Use severity.
- Add `for` windows.
- Include runbook and dashboard.

## Quick Shell Scripting Exercises

### 1. Service Health Checker

Write a script that checks whether three services are active.

Expected approach:

```bash
#!/usr/bin/env bash
set -euo pipefail

for svc in order-router risk-engine market-data; do
  if systemctl is-active --quiet "$svc"; then
    echo "OK $svc"
  else
    echo "FAIL $svc"
  fi
done
```

### 2. Count 5xx Responses

Given access logs, count 5xx by path.

```bash
awk '$9 ~ /^5/ {print $7}' access.log | sort | uniq -c | sort -nr
```

### 3. Find Slow Requests

Given key-value logs with `latency_ms=`, print slow lines.

```bash
awk '
  {
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^latency_ms=/) {
        split($i, a, "=")
        if (a[2] > 1000) print $0
      }
    }
  }
' app.log
```

### 4. Cron-Safe Script

Requirements:

- Use full paths.
- Fail on errors.
- Log output.
- Prevent overlapping runs.

Cron:

```cron
*/5 * * * * flock -n /tmp/check.lock /opt/scripts/check.sh >> /var/log/check.log 2>&1
```

### 5. Disk Usage Alert Script

```bash
#!/usr/bin/env bash
set -euo pipefail

threshold=85
usage="$(df / | awk 'NR==2 {gsub("%","",$5); print $5}')"

if (( usage >= threshold )); then
  echo "CRITICAL disk usage ${usage}%"
  exit 2
fi

echo "OK disk usage ${usage}%"
```

## Most Important Docker Commands

```bash
docker build -t app:local .
docker images
docker ps
docker ps -a
docker run --rm -p 8080:8080 app:local
docker run --rm --env-file .env app:local
docker logs --tail 100 container_name
docker logs -f container_name
docker exec -it container_name sh
docker inspect container_name
docker stats
docker stop container_name
docker rm container_name
docker rmi image_name
docker compose up -d
docker compose ps
docker compose logs -f service_name
docker compose restart service_name
docker compose down
```

Interview explanations:

- `docker ps`: running containers.
- `docker ps -a`: includes stopped containers.
- `docker logs`: stdout/stderr from container.
- `docker exec`: run a command inside container.
- `docker inspect`: config, networking, mounts, env.
- `docker stats`: live resource usage.

## Practical Backend Debugging Workflows

### Workflow 1: Service Unavailable

```bash
curl -v --max-time 2 http://service:8080/health
systemctl status service
journalctl -u service --since "15 min ago"
ss -ltnp | grep 8080
```

Decision:

- No process: restart or investigate crash.
- Process alive, no port: startup/config issue.
- Port open, health fails: app/dependency issue.
- Health OK, users fail: load balancer/network/routing issue.

### Workflow 2: Latency Incident

```bash
grep "latency_ms=" app.log | tail
top -p "$(pgrep -f service | head -1)"
ss -tan | awk 'NR > 1 {print $1}' | sort | uniq -c | sort -nr
```

Then check dashboards:

- P95/P99 latency.
- Error rate.
- Queue depth.
- CPU/memory.
- Dependency latency.
- Deploy markers.

### Workflow 3: One Failed Order

```bash
grep -R "order_id=ORD-42" /var/log/order-router/
grep -R "client_order_id=ABC-123" /var/log/
grep -R "request_id=req-11" /var/log/
```

Answer path:

- API received order.
- Risk checked or rejected.
- Order sent to exchange or not.
- Exchange ack/reject/timeout.
- Final persisted state.

### Workflow 4: Many Failed Orders

```bash
grep "order_rejected" app.log \
  | awk -F'reason=' '{print $2}' \
  | awk '{print $1}' \
  | sort | uniq -c | sort -nr
```

Then split by:

- Exchange.
- Account.
- Symbol.
- Version.
- Host.
- Time window.

### Workflow 5: Suspected Bad Deploy

```bash
grep "version=" app.log | tail
journalctl -u service --since "30 min ago" | grep -E "Started|Stopped|version|deploy"
systemctl status service
```

Mitigation:

- Confirm version correlation.
- Roll back one instance or shift traffic.
- Verify metrics recover.
- Preserve logs for root cause.

## HFT Backend Infrastructure Engineering Tips

- Latency tail matters more than average latency.
- Always distinguish "order not sent", "order sent but unknown", and "order rejected".
- Use idempotency/client order IDs for order workflows.
- Avoid unbounded retries and queues in trading paths.
- Monitor exchange connectivity as a first-class signal.
- Market data gaps and feed lag are production incidents.
- Keep operational scripts deterministic and logged.
- Do not restart live trading services casually; check failover and blast radius.
- Design dashboards around business workflows, not only host metrics.
- Use monotonic clocks for measuring durations in code.
- Keep config changes auditable.
- Roll out changes gradually during sensitive trading windows.
- Prefer explicit timeouts everywhere.
- Separate critical trading work from reporting/analytics work.
- Treat "unknown state" as a serious production state, especially after network timeouts.

## Final One-Hour Revision Plan

1. Review `ps`, `top`, `ss`, `lsof`, `systemctl`, and `journalctl`.
2. Practice `grep`, `awk`, and `sed` on sample logs.
3. Memorize liveness vs readiness.
4. Memorize counter vs gauge vs histogram.
5. Practice explaining retry danger with duplicate orders.
6. Review Docker debugging commands.
7. Practice one full incident answer: latency spike, crashed service, rejected orders, disk full.
8. Keep answers practical: command, signal, interpretation, fix.
