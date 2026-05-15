# SSH Logs and Production Access

Tags: #ssh #scp #logs #incident-debugging #production-access #linux

## Why This Matters

Production backend work often requires secure remote access and fast log analysis. In HFT/trading environments, access is audited, changes are controlled, and debugging must minimize risk to live systems.

## SSH Basics

### Concept

SSH provides encrypted remote shell access.

```bash
ssh app@prod-order-router-01
```

With explicit key:

```bash
ssh -i ~/.ssh/prod_ed25519 app@10.10.4.12
```

With port:

```bash
ssh -p 2222 app@bastion.example.com
```

### SSH Keys

Generate key:

```bash
ssh-keygen -t ed25519 -C "aahan-prod-access"
```

Common files:

```text
~/.ssh/id_ed25519      private key, keep secret
~/.ssh/id_ed25519.pub  public key, can be shared
~/.ssh/authorized_keys allowed public keys on server
```

Permissions:

```bash
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

### SSH Config

```sshconfig
Host prod-bastion
  HostName bastion.example.com
  User app
  IdentityFile ~/.ssh/prod_ed25519
  IdentitiesOnly yes

Host order-router-01
  HostName 10.10.4.12
  User app
  ProxyJump prod-bastion
```

Usage:

```bash
ssh order-router-01
```

### Authentication Debugging

```bash
ssh -vvv order-router-01
```

Common errors:

```text
Permission denied (publickey).
```

Check:

```bash
ls -ld ~/.ssh
ls -l ~/.ssh/id_ed25519
ssh-add -l
```

### SCP Basics

Copy local file to remote:

```bash
scp ./check.sh app@order-router-01:/tmp/check.sh
```

Copy remote logs locally:

```bash
scp app@order-router-01:/var/log/order-router/app.log ./app.log
```

For larger or resumable transfers, prefer `rsync`:

```bash
rsync -avz app@order-router-01:/var/log/order-router/ ./logs/
```

## Secure Production Access

Best practices:

- Use SSH keys, not passwords.
- Use a bastion/jump host for private servers.
- Enforce least privilege and audited access.
- Disable direct root login.
- Rotate keys when engineers leave or keys are exposed.
- Avoid copying production secrets to laptops.
- Use read-only access for investigation when possible.

Production mistake:

```bash
ssh root@prod-host
```

Better:

```bash
ssh app@prod-host
sudo systemctl status order-router
```

## Log Analysis

### Concept

Logs are timestamped facts emitted by services. In backend production systems, good logs help trace requests, orders, exchange sessions, retries, latency, state transitions, and failures.

### Basic Commands

```bash
tail -n 100 /var/log/order-router/app.log
tail -f /var/log/order-router/app.log
less /var/log/order-router/app.log
grep -n "ERROR" /var/log/order-router/app.log
grep -C 5 "order_id=ORD-9912" /var/log/order-router/app.log
```

Compressed logs:

```bash
zgrep "order_id=ORD-9912" /var/log/order-router/app.log.1.gz
```

### Filtering Logs

```bash
# Last 100 errors
grep "level=ERROR" app.log | tail -100

# One request across logs
grep -R "request_id=req-8f12" /var/log/order-router/

# Slow requests
grep "latency_ms=" app.log | awk '
  {
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^latency_ms=/) {
        split($i, a, "=")
        if (a[2] > 500) print $0
      }
    }
  }
'
```

### Structured Logging Basics

Prefer logs that are easy to search:

```text
ts=2026-05-14T09:31:22Z level=ERROR service=order-router request_id=req-11 order_id=ORD-42 route=/orders error=exchange_timeout latency_ms=2100
```

Useful fields:

- `ts`
- `level`
- `service`
- `host`
- `request_id`
- `order_id`
- `account_id` or anonymized customer identifier
- `exchange`
- `latency_ms`
- `error`
- `version`

Avoid:

```text
Something failed!!!
```

This has no searchable cause, ID, or impact.

### JSON Log Example

```json
{"ts":"2026-05-14T09:31:22Z","level":"ERROR","service":"order-router","request_id":"req-11","order_id":"ORD-42","error":"exchange_timeout","latency_ms":2100}
```

Useful with `jq` if installed:

```bash
jq 'select(.level=="ERROR") | {ts, request_id, order_id, error}' app.json.log
```

## Production Debugging Workflows

### Trace an Incident Window

```bash
START="2026-05-14T09:25"
grep "$START" /var/log/order-router/app.log
journalctl -u order-router --since "2026-05-14 09:25" --until "2026-05-14 09:40"
```

Then search for:

```bash
grep -E "deploy|restart|ERROR|timeout|disconnect|reconnect|rate_limit" app.log
```

### Count Error Types

```bash
grep "level=ERROR" app.log \
  | awk '
    {
      for (i = 1; i <= NF; i++) {
        if ($i ~ /^error=/) {
          split($i, a, "=")
          print a[2]
        }
      }
    }
  ' \
  | sort | uniq -c | sort -nr
```

Example:

```text
  381 exchange_timeout
   27 validation_error
    8 auth_rejected
```

Interpretation: likely dependency or network problem, not client input.

### Correlate Logs With Process State

```bash
grep "latency_ms=" app.log | tail -20
top -p "$(pgrep -f order-router | head -1)"
ss -tanp | grep order-router | awk '{print $1}' | sort | uniq -c
```

If latency grows with `SYN-SENT`, suspect dependency connectivity. If latency grows with CPU, suspect application pressure. If latency grows with `CLOSE-WAIT`, suspect socket cleanup bug.

### Debugging Crashed Services

```bash
systemctl status order-router
journalctl -u order-router --since "30 min ago" -n 200
systemctl show order-router --property=NRestarts
```

Look for:

- Exception trace.
- Config parse failure.
- Permission denied.
- Port conflict.
- Missing dependency.
- OOM kill.

Check kernel messages:

```bash
dmesg -T | grep -i "killed process"
```

Example:

```text
Out of memory: Killed process 1234 (python) total-vm:4096000kB
```

Production interpretation: process may need memory limits, leak investigation, queue bounds, or host capacity review.

## Interview Questions

- "How do you securely access production servers?"
  - Answer: Use bastions/VPN, MFA, least privilege, named accounts, audited access, and read-only investigation before privileged changes.
- "Why is SSH private key permission important?"
  - Answer: Anyone who can read the private key can impersonate that identity, so permissions must be restricted.
- "How do you trace one failed order across logs?"
  - Answer: Use request ID, client order ID, exchange order ID, timestamps, service names, and correlated logs across API, router, connector, and worker.
- "What fields should production logs include?"
  - Answer: Include timestamp, service, host, version, environment, request/order IDs, latency, status, error code, and sanitized context.
- "What is the difference between logs and metrics?"
  - Answer: Logs are event records for specific failures; metrics are numeric aggregates for trends, alerting, and dashboards.
- "How do you debug an OOM-killed service?"
  - Answer: Check `dmesg`, service logs, memory metrics, `docker stats`/cgroup limits, heap/profile evidence, queue depth, and recent traffic/deploy changes.
- "How do you avoid leaking secrets in logs?"
  - Answer: Redact tokens/keys, avoid env dumps or signed payloads, use structured allowlisted fields, and review exception messages.

Warning: avoid jumping straight to SSH and restart. Collect evidence, check impact, verify failover, then act.

## Performance and Reliability Considerations

- Logging too much on hot paths can increase latency and disk IO.
- Logging too little slows incident response.
- Avoid synchronous remote logging in latency-critical request paths.
- Redact secrets, tokens, credentials, and PII.
- Include correlation IDs so distributed workflows can be traced.
- Rotate logs; disk-full incidents are common and avoidable.

## Common Mistakes

- No request/order correlation ID.
- Multi-line logs that are hard to grep.
- Logging stack traces without business identifiers.
- Logging secrets in exceptions or environment dumps.
- Searching entire log history instead of narrowing by time window.
- Copying production data locally unnecessarily.
- Debugging as root when read-only access is enough.

## Quick Revision

- SSH uses public/private key authentication; keep private keys `600`.
- Use bastions and least privilege for production access.
- Logs should include IDs, service, host, version, latency, and error fields.
- Always narrow log searches by time, service, request ID, or order ID.
- Correlate logs with service status, process state, socket state, and metrics.
