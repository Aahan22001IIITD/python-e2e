# Linux Infra Monitoring Reliability

Tags: #linux #infra #monitoring #reliability #backend #hft #interview

Role focus: Python backend services supporting trading workflows, exchange connectivity, automation, production Linux hosts, observability, incident debugging, and high-uptime backend infrastructure.

Use these notes for fast interview revision:

## Linux + Infrastructure

- [[01 Shell Scripting and Text Processing]] — bash, variables, loops, functions, `grep`, `awk`, `sed`, log processing
- [[02 Permissions Environment and Scheduling]] — `chmod`, file permissions, environment variables, secrets/config, cron jobs
- [[03 Processes Services and Network Debugging]] — `ps`, `top`, `netstat`, `ss`, `lsof`, process monitoring, `systemctl`
- [[04 SSH Logs and Production Access]] — SSH keys, SCP, secure access, log analysis, structured logging, incident tracing
- [[05 Docker and Ansible Basics]] — containers, Dockerfiles, ports, volumes, compose, production debugging, Ansible playbooks

## Monitoring + Reliability

- [[06 Monitoring Prometheus Grafana and Alerting]] — Prometheus, scraping, exporters, PromQL, Grafana dashboards, metrics vs logs, structured logging, alerting pipelines
- [[07 Reliability Health Checks Retries and Incidents]] — uptime, SLOs, liveness/readiness, retries, circuit breakers, fault tolerance, outage debugging

## Final Revision

- [[08 Revision Bank Scenarios and Commands]] — top reliability questions, outage debugging, backend failure fixes, Prometheus/Grafana revision, HFT incident scenarios

## Interview Answer Pattern

For Linux/infrastructure questions, answer in this order:

1. State the command or concept precisely.
2. Explain what signal it gives in production.
3. Show the command you would run.
4. Explain how you would interpret the output.
5. Mention the reliability or security risk.
6. Close with the production-safe fix.

Example:

```bash
# API latency spike on a trading backend
systemctl status order-router
journalctl -u order-router --since "15 min ago" -p warning
ss -tanp | grep ':443'
top -p "$(pgrep -f order-router | head -1)"
```

Strong interview answers sound operational: "I would first check whether the process is alive, whether it is accepting connections, whether latency correlates with CPU/memory/IO, and then correlate logs with metrics around the incident window."

## HFT Backend Bias

- Prefer fast diagnosis over broad theory.
- Know how to inspect a Linux host without installing tools.
- Treat logs, metrics, traces, and process state as one debugging story.
- Be careful with restarts during market hours; verify impact and failover first.
- Automate repeated checks, but keep scripts simple and observable.
- Never hide failures in cron, shell scripts, retries, or health checks.
