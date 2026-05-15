# Processes Services and Network Debugging

Tags: #linux #processes #systemctl #top #ps #lsof #netstat #ss #debugging

## Why This Matters

Backend production incidents often begin with simple questions: is the process running, is it using too much CPU or memory, is it listening on the expected port, is it stuck, and can it reach dependencies? These commands are the fastest path from vague outage to concrete signal.

## Process Monitoring

### Process Lifecycle

Common states:

- Running: executing or ready to run.
- Sleeping: waiting for IO, network, timer, or lock.
- Zombie: exited, but parent has not collected exit status.
- Stopped: paused by signal/debugger.

```bash
ps aux | grep order-router
ps -ef | grep '[o]rder-router'
pgrep -af order-router
```

The `[o]rder-router` trick avoids matching the `grep` command itself.

### ps

```bash
ps aux --sort=-%cpu | head
ps aux --sort=-%mem | head
ps -o pid,ppid,stat,%cpu,%mem,etime,cmd -p 1234
```

Example:

```text
PID  PPID STAT %CPU %MEM     ELAPSED CMD
1234    1 Sl   92.1 12.4    03:42:18 python -m order_router
```

Interpretation:

- High CPU with rising latency may indicate busy loop, serialization overhead, compression, bad regex, or overload.
- High memory may indicate leak, cache growth, unbounded queue, or large batch processing.
- Long elapsed time confirms it has not recently restarted.

### top

```bash
top
top -p 1234
```

Useful signals:

- `%CPU`: CPU pressure from process.
- `%MEM`: memory share.
- `load average`: runnable or blocked work.
- `wa`: IO wait, useful when disk/network storage is slow.

Warning: high load does not always mean CPU saturation. Load can rise from IO waits too.

### Identifying Stuck Processes

```bash
ps -o pid,stat,wchan,cmd -p 1234
```

Example:

```text
PID  STAT WCHAN  CMD
1234 S    futex_ python -m order_router
```

Interpretation: process may be waiting on a lock or thread synchronization.

For Python:

```bash
kill -USR1 1234
```

Only use this if the application is configured to dump stack traces on `SIGUSR1`. Otherwise it may do nothing or behave unexpectedly.

### Zombie Processes

```bash
ps aux | awk '$8 ~ /Z/ {print}'
```

Example:

```text
app 22118 0.0 0.0 0 0 ? Z 09:14 0:00 [python] <defunct>
```

Production meaning: the parent process is not reaping children. A few short-lived zombies may be harmless; growing zombies indicate a process management bug.

## CPU and Memory Bottlenecks

```bash
free -h
vmstat 1 5
df -h
du -sh /var/log/order-router
```

Example `vmstat`:

```text
r  b  swpd  free  buff cache  si so  bi bo  in  cs us sy id wa
8  0     0  120M  80M  900M    0  0   1  4 900 450 88  7  3  2
```

Interpretation:

- High `r`: CPU run queue pressure.
- High `wa`: IO wait.
- `si/so`: swapping, often bad for latency-sensitive services.

HFT/backend point: swapping is dangerous for latency. Avoid memory overcommit for critical trading paths.

## Port and Network Debugging

### ss and netstat

`ss` is the modern replacement for `netstat` on many Linux systems.

```bash
ss -ltnp
ss -tanp | grep ':8080'
netstat -tulpen
```

Examples:

```text
LISTEN 0 4096 0.0.0.0:8080 0.0.0.0:* users:(("python",pid=1234,fd=12))
```

Interpretation: process `1234` is listening on port `8080`.

```bash
# Count TCP connection states
ss -tan | awk 'NR > 1 {print $1}' | sort | uniq -c | sort -nr
```

Output:

```text
  821 ESTAB
  142 TIME-WAIT
   23 SYN-SENT
```

Production meaning:

- Many `SYN-SENT`: outbound connection attempts may be blocked or dependency unreachable.
- Many `TIME-WAIT`: high connection churn; connection pooling may be missing.
- Many `CLOSE-WAIT`: application may not be closing sockets.

### lsof

```bash
lsof -i :8080
lsof -p 1234
lsof -Pan -p 1234 -i
```

Find deleted files still held open:

```bash
lsof | grep deleted
```

Production scenario: disk is full even after deleting logs because a process still holds deleted file handles.

Fix:

```bash
sudo systemctl restart order-router
```

Do this only after checking impact.

### Port Already in Use

Error:

```text
OSError: [Errno 98] Address already in use
```

Debug:

```bash
sudo lsof -i :8080
sudo ss -ltnp 'sport = :8080'
```

Fix depends on ownership:

- Stop the old service if it should not run.
- Change port if two services legitimately conflict.
- Fix service unit if duplicate instances are being started.

## systemctl

### Concept

`systemctl` manages systemd services. Most production Linux services run under systemd or an equivalent process supervisor.

### Commands

```bash
systemctl status order-router
sudo systemctl start order-router
sudo systemctl stop order-router
sudo systemctl restart order-router
sudo systemctl reload order-router
sudo systemctl enable order-router
sudo systemctl disable order-router
```

`reload` asks the process to reload config without full restart if supported. `restart` kills and starts the process.

### Logs

```bash
journalctl -u order-router
journalctl -u order-router --since "30 min ago"
journalctl -u order-router -f
journalctl -u order-router -p warning --since today
```

Example status:

```text
Active: activating (auto-restart) (Result: exit-code)
Main PID: 18420 (code=exited, status=1/FAILURE)
```

Interpretation: restart loop, likely bad config, missing dependency, failed migration, or runtime exception at startup.

### Inspecting a Service Unit

```bash
systemctl cat order-router
systemctl show order-router --property=User,Restart,Environment
```

Example:

```ini
[Service]
User=order-router
EnvironmentFile=/etc/order-router.env
ExecStart=/opt/order-router/venv/bin/python -m order_router
Restart=on-failure
RestartSec=3
```

Production relevance:

- `User` controls privilege.
- `EnvironmentFile` controls config source.
- `Restart` controls recovery behavior.
- `RestartSec` prevents tight crash loops.

## Production Troubleshooting Examples

### Service Is Down

```bash
systemctl status order-router
journalctl -u order-router --since "15 min ago" -n 100
systemctl cat order-router
ls -l /etc/order-router.env
```

Likely causes:

- Bad config.
- Missing env file.
- Permission error.
- Port conflict.
- Failed dependency.

### API Is Slow but Service Is Running

```bash
top -p "$(pgrep -f order-router | head -1)"
ss -tanp | grep order-router | awk '{print $1}' | sort | uniq -c
journalctl -u order-router --since "10 min ago" -p warning
```

Interpretation:

- High CPU: code path, serialization, compression, bad loop.
- High memory/swap: leak or unbounded queue.
- Many outbound connections: missing pooling or dependency latency.
- Many warnings: retries, timeouts, queue delays.

### Service Cannot Bind Port

```bash
journalctl -u order-router --since "5 min ago"
sudo lsof -i :8080
sudo systemctl status old-order-router
```

Fix carefully. Do not kill unknown processes without identifying owner and impact.

## Interview Questions

- "What is the difference between `ps`, `top`, and `systemctl`?"
  - Answer: `ps` shows process snapshots, `top` shows live resource usage, and `systemctl` manages service lifecycle/state.
- "How do you know which process owns a port?"
  - Answer: Use `ss -ltnp`, `lsof -i :PORT`, or `fuser` to map a listening port to a PID and command.
- "What does `CLOSE-WAIT` indicate?"
  - Answer: The peer closed but the local app has not closed its socket, often pointing to leaked connections or stuck cleanup.
- "Why can disk remain full after deleting a log file?"
  - Answer: A running process may still hold the deleted file descriptor open.
- "What is a zombie process?"
  - Answer: A process that has exited but whose parent has not reaped its exit status.
- "When would you use `reload` instead of `restart`?"
  - Answer: Use `reload` when the service supports config reload without dropping connections; use `restart` when process state must be recreated.
- "What does a systemd restart loop look like?"
  - Answer: Repeated start/fail entries in `systemctl status` and `journalctl`, often with increasing restart counters.

Strong answers connect command output to production action.

## Best Practices

- Use systemd or a supervisor, not manual `nohup` for production services.
- Give each service a dedicated user.
- Prefer `ss` over old `netstat` when available.
- Validate config before restart if the service supports it.
- Check logs before and after restarting.
- Avoid killing processes until you know what they own.
- Monitor process CPU, memory, restarts, file descriptors, and socket states.

## Common Mistakes

- Treating "process exists" as "service healthy".
- Restarting during an incident without collecting evidence.
- Ignoring `CLOSE-WAIT`, file descriptor growth, or restart counts.
- Running services as root.
- Using `kill -9` as the first response.
- Forgetting that `localhost` inside a container is not the host.

## Quick Revision

- `ps` shows process snapshot.
- `top` shows live CPU/memory pressure.
- `ss`/`netstat` show sockets and connection states.
- `lsof` maps files/ports to processes.
- `systemctl` manages services; `journalctl` shows service logs.
- Always connect process state, logs, ports, and metrics before changing production state.
