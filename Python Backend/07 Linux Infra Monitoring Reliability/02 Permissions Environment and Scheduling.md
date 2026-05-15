# Permissions Environment and Scheduling

Tags: #linux #chmod #permissions #environment #cron #security #automation

## Why This Matters

Production backend systems depend on correct permissions, predictable configuration, and reliable scheduled automation. A trading support script that cannot execute, a secret exposed through environment dumps, or a silent cron failure can become a real incident.

## chmod and File Permissions

### Concept

Linux permissions control who can read, write, or execute a file.

```text
-rwxr-x--- 1 deploy trading 2180 May 14 09:30 restart_order_router.sh
```

Meaning:

- Owner `deploy`: read, write, execute
- Group `trading`: read, execute
- Others: no access

Permission bits:

- `r = 4`
- `w = 2`
- `x = 1`

Common modes:

- `600`: owner read/write only, useful for private keys
- `644`: owner write, everyone read, common config/file default
- `640`: owner write, group read, safer service config
- `755`: executable by everyone, common for scripts/binaries
- `750`: executable only by owner/group, safer production script mode

### Commands

```bash
ls -l deploy.sh
chmod +x deploy.sh
chmod 750 deploy.sh
chmod 640 /etc/order-router.env
chmod 600 ~/.ssh/id_ed25519
```

### Executable Scripts

```bash
cat ./check_orders.sh
```

```bash
#!/usr/bin/env bash
set -euo pipefail
curl -fsS --max-time 2 http://127.0.0.1:8080/health
```

```bash
chmod 750 check_orders.sh
./check_orders.sh
```

If execution fails:

```text
zsh: permission denied: ./check_orders.sh
```

Fix:

```bash
chmod +x ./check_orders.sh
```

### Security Implications

```bash
# Dangerous: secrets readable by all users
-rw-r--r-- 1 app app 900 .env

# Better
chmod 600 .env
```

```bash
# Dangerous on SSH private keys
chmod 777 ~/.ssh/id_ed25519

# Correct
chmod 600 ~/.ssh/id_ed25519
```

SSH may reject permissive private keys:

```text
WARNING: UNPROTECTED PRIVATE KEY FILE!
Permissions 0644 for 'id_ed25519' are too open.
```

### Production Mistakes

- Using `chmod 777` to "make it work".
- Making secrets world-readable.
- Forgetting execute permission on deployment or health check scripts.
- Running services as `root` when a dedicated service user is enough.
- Changing ownership recursively on the wrong path.

```bash
# Dangerous if variable is empty
sudo chown -R app:app "$APP_DIR"
```

Safer:

```bash
: "${APP_DIR:?APP_DIR is required}"
sudo chown -R app:app "$APP_DIR"
```

## Environment Variables

### Concept

Environment variables configure processes without hardcoding values in code. Backend systems use them for ports, URLs, feature flags, credentials references, log levels, and runtime behavior.

```bash
export APP_ENV=prod
export PORT=8080
export LOG_LEVEL=INFO
python app.py
```

Only exported variables are inherited by child processes.

```bash
APP_ENV=prod
echo "$APP_ENV"       # visible in current shell

export APP_ENV=prod
python -c 'import os; print(os.getenv("APP_ENV"))'
```

### One-Command Environment

```bash
LOG_LEVEL=DEBUG python app.py
```

This affects only that process invocation.

### Inspecting Process Environment

```bash
tr '\0' '\n' < /proc/1234/environ
```

On macOS this exact `/proc` path is unavailable, but on Linux production hosts it is common.

### Backend Configuration Management

Systemd service example:

```ini
[Service]
EnvironmentFile=/etc/order-router.env
ExecStart=/opt/order-router/venv/bin/python -m order_router
User=order-router
Restart=on-failure
```

Environment file:

```bash
APP_ENV=prod
PORT=8080
EXCHANGE_GATEWAY_URL=tcp://10.10.4.8:9001
LOG_LEVEL=INFO
```

### Secrets and Config Handling

Best practice:

- Use environment variables for non-secret config and secret references.
- Use secret managers or restricted files for real secrets.
- Avoid printing all environment variables in logs.
- Keep `/etc/*.env` readable only by the service user/root.

```bash
sudo chmod 640 /etc/order-router.env
sudo chown root:order-router /etc/order-router.env
```

### Warning

Question: "Is putting secrets in environment variables always safe?"

Answer: No. Env vars can leak through process inspection, crash dumps, logs, shell history, debugging endpoints, or child processes. They are common, but access control and logging discipline still matter.

## Cron Jobs

### Concept

Cron schedules recurring commands. Backend teams use it for cleanup, reconciliation, reports, backups, cache warmups, cert checks, and operational automation.

### Cron Syntax

```text
* * * * * command
| | | | |
| | | | day of week
| | | month
| | day of month
| hour
minute
```

Examples:

```cron
# Every minute
* * * * * /opt/scripts/check_feed_gap.sh

# Every weekday at 08:55
55 8 * * 1-5 /opt/scripts/pre_market_checks.sh

# Every night at 02:30
30 2 * * * /opt/scripts/archive_logs.sh
```

Edit cron:

```bash
crontab -e
crontab -l
```

### Production Cron Example

```cron
*/5 * * * * /opt/scripts/check_order_lag.sh >> /var/log/order-lag-cron.log 2>&1
```

Script:

```bash
#!/usr/bin/env bash
set -euo pipefail

MAX_LAG_SECONDS=3
lag="$(/opt/order-tools/current_lag_seconds)"

if (( lag > MAX_LAG_SECONDS )); then
  echo "$(date -Is) CRITICAL order lag ${lag}s"
  exit 2
fi

echo "$(date -Is) OK order lag ${lag}s"
```

### Production Pitfalls

- Cron has a minimal environment; `PATH`, virtualenv, and app variables may be missing.
- Output may go to local mail instead of central logs.
- Overlapping jobs can corrupt state or overload dependencies.
- Time zones and daylight saving time can surprise schedules.
- Silent failures are common when exit codes are ignored.

Safer cron:

```cron
SHELL=/bin/bash
PATH=/usr/local/bin:/usr/bin:/bin

*/5 * * * * flock -n /tmp/reconcile.lock /opt/scripts/reconcile.sh >> /var/log/reconcile.log 2>&1
```

`flock` prevents overlapping runs.

### Debugging Cron

```bash
crontab -l
grep CRON /var/log/syslog
journalctl -u cron --since "1 hour ago"
ls -l /opt/scripts/reconcile.sh
sudo -u app /opt/scripts/reconcile.sh
```

Common output:

```text
/bin/sh: 1: python: not found
```

Fix: use full paths.

```cron
*/5 * * * * /opt/app/venv/bin/python /opt/app/jobs/reconcile.py
```

## Interview Debugging Examples

### Script Works Manually but Fails in Cron

Check:

```bash
crontab -l
env -i /bin/bash -lc '/opt/scripts/reconcile.sh'
ls -l /opt/scripts/reconcile.sh
journalctl -u cron --since today
```

Likely causes:

- Missing environment variables.
- Wrong working directory.
- Wrong shell.
- Missing executable permission.
- Relative paths.

Production fix:

- Use absolute paths.
- Explicitly load config.
- Log stdout/stderr.
- Use `flock` for non-overlap.

### Service Fails After Config Permission Change

```bash
systemctl status order-router
journalctl -u order-router --since "10 min ago"
ls -l /etc/order-router.env
```

Bad output:

```text
-rw------- 1 root root 840 /etc/order-router.env
Permission denied: '/etc/order-router.env'
```

Fix:

```bash
sudo chown root:order-router /etc/order-router.env
sudo chmod 640 /etc/order-router.env
sudo systemctl restart order-router
```

## Performance and Reliability Considerations

- Cron jobs should be idempotent where possible.
- Scripts should fail loudly and emit enough context to debug.
- Avoid running heavy cron jobs during market open/close unless intentional.
- Protect scripts and env files with least privilege.
- Prefer systemd timers for more observable production scheduling when available.

## Quick Revision

- `chmod 750 script.sh` is safer than `777`.
- Private SSH keys should usually be `600`.
- Exported env vars are inherited by child processes.
- Cron needs explicit paths and logging.
- Use `flock` to prevent overlapping scheduled jobs.
- Secrets are not automatically safe just because they are env vars.
