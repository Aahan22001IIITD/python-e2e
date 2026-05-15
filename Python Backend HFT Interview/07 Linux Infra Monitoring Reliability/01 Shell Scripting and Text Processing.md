# Shell Scripting and Text Processing

Tags: #linux #bash #grep #awk #sed #logs #automation #interview

## Why This Matters

Backend/HFT engineers often debug production before a full observability view is available. Shell scripting and text tools let you inspect logs, validate deployments, automate checks, and answer: "What changed, what is failing, and how many users/orders/sessions are affected?"

Use shell tools for quick diagnosis and automation, not as a replacement for tested application code.

## Basic Shell Scripting

### Concept

A shell script is a repeatable sequence of Linux commands. In production it is used for health checks, log rotation helpers, deployment hooks, backup checks, config validation, and incident triage.

```bash
#!/usr/bin/env bash
set -euo pipefail

SERVICE="order-router"
LOG="/var/log/order-router/app.log"

echo "Checking $SERVICE"
systemctl is-active --quiet "$SERVICE"
tail -n 20 "$LOG"
```

`set -euo pipefail` means:

- `-e`: fail on command error
- `-u`: fail on unset variables
- `pipefail`: fail if any command in a pipeline fails

### Variables

```bash
ENVIRONMENT="prod"
HOSTNAME="$(hostname)"
TODAY="$(date +%F)"

echo "Running on $HOSTNAME in $ENVIRONMENT at $TODAY"
```

Use quotes around variables unless you intentionally want word splitting.

```bash
# Safer
rm -f "$OUTPUT_FILE"

# Risky if OUTPUT_FILE is empty or has spaces
rm -f $OUTPUT_FILE
```

### Conditionals

```bash
if systemctl is-active --quiet risk-engine; then
  echo "risk-engine is running"
else
  echo "risk-engine is DOWN"
  exit 1
fi
```

### Loops

```bash
for svc in order-router market-data risk-engine; do
  if systemctl is-active --quiet "$svc"; then
    echo "OK $svc"
  else
    echo "FAIL $svc"
  fi
done
```

### Functions

```bash
check_port() {
  local port="$1"
  if ss -ltn | awk '{print $4}' | grep -q ":${port}$"; then
    echo "OK port $port is listening"
  else
    echo "FAIL port $port is not listening"
    return 1
  fi
}

check_port 8080
```

### Script Execution

```bash
chmod +x check_backend.sh
./check_backend.sh

# Run with explicit shell
bash check_backend.sh
```

### Backend Automation Example

```bash
#!/usr/bin/env bash
set -euo pipefail

URL="http://127.0.0.1:8080/health"

response="$(curl -fsS --max-time 2 "$URL")"
echo "$response" | grep -q '"status":"ok"'

echo "backend healthy"
```

Expected failure style:

```text
curl: (28) Operation timed out after 2001 milliseconds
```

Production interpretation: process may be alive, but request handling is blocked, dependency calls are hanging, or the service is overloaded.

### Log Processing Example

```bash
# Count failed orders by reason in the last rotated log
grep "order_rejected" /var/log/order-router/app.log \
  | awk -F'reason=' '{print $2}' \
  | awk '{print $1}' \
  | sort \
  | uniq -c \
  | sort -nr
```

Example output:

```text
  182 risk_limit
   47 invalid_symbol
    9 exchange_closed
```

## grep

### Concept

`grep` searches text using literal strings or regular expressions. In production, it is used to find errors, request IDs, order IDs, stack traces, reconnects, auth failures, and deployment markers.

### Common Commands

```bash
# Search one file
grep "ERROR" app.log

# Case-insensitive search
grep -i "timeout" app.log

# Show line numbers
grep -n "order_id=ABC123" app.log

# Show context around a match
grep -C 3 "Connection reset" app.log

# Recursive search
grep -R "exchange_disconnect" /var/log/order-router/

# Extended regex
grep -E "ERROR|WARN|CRITICAL" app.log

# Count matches
grep -c "order_rejected" app.log
```

### Production Log Filtering

```bash
# Follow logs and show only severe lines
tail -f /var/log/order-router/app.log | grep -E "ERROR|CRITICAL|timeout|disconnect"
```

```bash
# Trace one request or order through logs
grep -R "request_id=req-8f12" /var/log/*/
grep -R "order_id=ORD-9912" /var/log/order-router/
```

### Regex Basics

```bash
grep -E "5[0-9]{2}" access.log       # HTTP 500-599
grep -E "latency_ms=[1-9][0-9]{3,}" app.log
grep -E "\b(retry|timeout)\b" app.log
```

### Interview Traps

- `grep error` is case-sensitive; use `grep -i error` when logs vary.
- `grep "500"` can match timestamps or order IDs; prefer structured fields like `status=500`.
- Recursive `grep -R /` can be dangerous and slow on production hosts.
- `grep` on compressed logs needs `zgrep`.

```bash
zgrep "order_id=ORD-9912" /var/log/order-router/app.log.1.gz
```

## awk Basics

### Concept

`awk` processes text as fields and records. It is useful for columns, logs, counters, and quick monitoring.

Default field separator is whitespace.

```bash
awk '{print $1, $4, $9}' access.log
```

### Column Processing

```bash
# Print PID and command from ps output
ps aux | awk '{print $2, $11}'

# Sum request counts from a file
awk '{sum += $1} END {print sum}' counts.txt
```

### Log Parsing

```bash
# access.log format: ip - - [time] "GET /path HTTP/1.1" status bytes
awk '$9 >= 500 {print $1, $7, $9}' access.log
```

Example output:

```text
10.2.1.44 /orders 503
10.2.1.45 /risk/check 500
```

### Backend Monitoring Example

```bash
# Extract high latency app log lines:
# ts=... route=/orders status=200 latency_ms=1242
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

### Quick Automation Usage

```bash
# Top source IPs from access logs
awk '{print $1}' access.log | sort | uniq -c | sort -nr | head
```

```text
 9231 10.0.4.21
 1120 10.0.8.19
  994 10.0.2.77
```

Production interpretation: one client or service may be retrying aggressively.

## sed Basics

### Concept

`sed` edits streams of text. Use it for safe substitutions, extracting ranges, and automation. Be careful with in-place edits on configs.

### Text Replacement

```bash
echo "env=staging" | sed 's/staging/prod/'
```

Output:

```text
env=prod
```

### Stream Editing

```bash
# Replace only first match per line
sed 's/DEBUG/INFO/' app.conf

# Replace all matches per line
sed 's/DEBUG/INFO/g' app.conf

# Print lines 100 to 130
sed -n '100,130p' app.log
```

### Config Modification Example

```bash
# Preview change first
sed 's/^LOG_LEVEL=.*/LOG_LEVEL=INFO/' /etc/order-router.env

# In-place change with backup
sudo sed -i.bak 's/^LOG_LEVEL=.*/LOG_LEVEL=INFO/' /etc/order-router.env
```

### Production Caution

Before editing configs:

```bash
sudo cp /etc/order-router.env /etc/order-router.env.$(date +%F-%H%M%S).bak
sudo systemctl reload order-router
sudo systemctl status order-router
```

Common mistake: using broad replacements.

```bash
# Bad: may change URLs, comments, unrelated names
sed -i 's/prod/staging/g' config.env

# Better: only change the intended key
sed -i 's/^ENV=.*/ENV=staging/' config.env
```

## Interview Debugging Example

Question: "Orders are failing after deploy. You only have shell access. What do you do?"

```bash
systemctl status order-router
journalctl -u order-router --since "30 min ago" -p warning
grep -R "order_rejected\|ERROR\|timeout" /var/log/order-router/
grep "deploy_version" /var/log/order-router/app.log | tail
awk '/order_rejected/ {print}' /var/log/order-router/app.log | tail -20
```

Answer:

- Confirm service health and restart loop state.
- Correlate failures with deployment time/version.
- Search for structured error fields, not vague strings only.
- Count failure reasons to separate one bad client from system-wide failure.
- Roll back only after identifying blast radius or if error rate is severe.

## Performance and Reliability Considerations

- Use `grep`/`awk` on narrowed files and time windows; full filesystem scans can overload hosts.
- Prefer structured logs with keys like `order_id=`, `request_id=`, `latency_ms=`.
- Avoid long shell scripts with complex business logic.
- Add timeouts to scripts that call networks: `curl --max-time 2`.
- Scripts run by cron should log stdout/stderr.

## Common Mistakes

- Forgetting quotes around variables.
- Ignoring exit codes in scripts.
- Writing scripts that silently continue after failures.
- Running expensive recursive searches on production boxes.
- Using `sed -i` without backup or validation.
- Parsing human-formatted logs when structured JSON/key-value logs are available.

## Quick Revision

- `grep` finds lines, `awk` extracts/aggregates fields, `sed` transforms streams.
- Always narrow by service, time window, request ID, order ID, or error type.
- Shell scripts should use `set -euo pipefail`, quotes, explicit timeouts, and useful logs.
- In interviews, explain both the command and how you interpret the output.
