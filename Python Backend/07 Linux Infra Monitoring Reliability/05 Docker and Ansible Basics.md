# Docker and Ansible Basics

Tags: #docker #containers #ansible #infra #deployment #backend #automation

## Why This Matters

Backend services are commonly packaged in containers and deployed through automation. In interviews, the important skill is not reciting Docker theory; it is explaining how to build, run, inspect, debug, and automate services safely.

## Docker Basics

### Containers vs VMs

A container is an isolated process with its own filesystem, environment, network namespace, and resource limits. It shares the host kernel. A VM runs a full guest OS with its own kernel.

Production relevance:

- Containers are fast to start and easy to package.
- They improve deployment consistency.
- They are not a security boundary equal to a VM.
- Host kernel, networking, storage, and cgroups still matter.

### Images vs Containers

- Image: immutable package/template.
- Container: running or stopped instance of an image.

```bash
docker images
docker ps
docker ps -a
```

Example:

```text
CONTAINER ID IMAGE                 STATUS        PORTS
aa12bb34cc   order-router:1.42.0   Up 3 hours    0.0.0.0:8080->8080/tcp
```

### Dockerfile Basics

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

CMD ["python", "-m", "order_router"]
```

Production notes:

- Pin dependencies.
- Keep images small.
- Avoid baking secrets into images.
- Run as non-root where possible.
- Emit logs to stdout/stderr.

Non-root example:

```dockerfile
RUN useradd --create-home appuser
USER appuser
```

### Build and Run

```bash
docker build -t order-router:local .
docker run --rm -p 8080:8080 order-router:local
```

With env:

```bash
docker run --rm \
  -e APP_ENV=prod \
  -e LOG_LEVEL=INFO \
  -p 8080:8080 \
  order-router:1.42.0
```

With env file:

```bash
docker run --rm --env-file ./order-router.env -p 8080:8080 order-router:1.42.0
```

### Ports

```bash
docker run -p 8080:8000 app
```

Meaning: host port `8080` forwards to container port `8000`.

Common mistake: app listens on `127.0.0.1` inside the container. It should usually listen on `0.0.0.0`.

```bash
python -m app --host 0.0.0.0 --port 8000
```

### Volumes

```bash
docker run --rm \
  -v /var/log/order-router:/app/logs \
  order-router:1.42.0
```

Use cases:

- Persist logs/data.
- Mount config.
- Share files with host.

Production caution: container-local filesystem can disappear when the container is removed.

### Docker Compose Basics

```yaml
services:
  order-router:
    image: order-router:1.42.0
    ports:
      - "8080:8080"
    env_file:
      - order-router.env
    depends_on:
      - redis

  redis:
    image: redis:7
```

Commands:

```bash
docker compose up -d
docker compose ps
docker compose logs -f order-router
docker compose restart order-router
docker compose down
```

### Production Debugging

```bash
docker ps
docker logs --tail 100 order-router
docker logs -f order-router
docker inspect order-router
docker exec -it order-router sh
docker stats
```

Check environment:

```bash
docker exec order-router env | sort
```

Check listening ports inside container:

```bash
docker exec order-router ss -ltnp
```

Check app health:

```bash
curl -fsS http://127.0.0.1:8080/health
```

### Common Docker Failure Scenarios

#### Container Exits Immediately

```bash
docker ps -a
docker logs order-router
```

Likely causes:

- Bad command.
- Missing environment variable.
- Config parse failure.
- Dependency unavailable at startup.

#### Cannot Reach Service

```bash
docker ps
docker port order-router
docker logs order-router
docker exec order-router ss -ltnp
```

Likely causes:

- Port not published.
- App bound to `127.0.0.1` inside container.
- Wrong container port.
- Host firewall/security group.

#### Works Locally, Fails in Container

Check:

```bash
docker exec order-router pwd
docker exec order-router ls -l
docker exec order-router env
docker logs order-router
```

Likely causes:

- Missing file in image.
- Different working directory.
- Missing OS package.
- Missing env var.
- Network DNS difference.

### Docker Best Practices

- Keep one main process per container.
- Use health checks.
- Use explicit image tags; avoid mutable `latest` in production.
- Do not store secrets in Dockerfile layers.
- Add resource limits in production orchestration.
- Send logs to stdout/stderr.
- Build images reproducibly in CI.

## Ansible Basics

### Concept

Ansible automates infrastructure configuration over SSH using declarative playbooks. It is useful for installing packages, writing config files, managing services, deploying app versions, and enforcing host state.

Production relevance:

- Reduces manual server drift.
- Makes deployments repeatable.
- Documents operational changes.
- Helps manage many Linux hosts consistently.

### Inventory

```ini
[order_routers]
order-router-01 ansible_host=10.10.4.12
order-router-02 ansible_host=10.10.4.13

[market_data]
md-01 ansible_host=10.10.5.20
```

### Ping Hosts

```bash
ansible -i inventory.ini order_routers -m ping
```

Example:

```text
order-router-01 | SUCCESS => {"ping": "pong"}
```

### Playbook Example

```yaml
- name: Deploy order router
  hosts: order_routers
  become: true

  tasks:
    - name: Install system packages
      apt:
        name:
          - python3
          - python3-venv
        state: present
        update_cache: true

    - name: Write environment file
      template:
        src: order-router.env.j2
        dest: /etc/order-router.env
        owner: root
        group: order-router
        mode: "0640"

    - name: Restart service
      systemd:
        name: order-router
        state: restarted
        enabled: true
```

Run:

```bash
ansible-playbook -i inventory.ini deploy-order-router.yml
```

Dry run:

```bash
ansible-playbook -i inventory.ini deploy-order-router.yml --check --diff
```

### Configuration Management

Template example:

```jinja2
APP_ENV={{ app_env }}
PORT={{ order_router_port }}
LOG_LEVEL={{ log_level }}
```

Variables:

```yaml
app_env: prod
order_router_port: 8080
log_level: INFO
```

### Backend Infrastructure Relevance

Use Ansible to:

- Install service dependencies.
- Manage systemd unit files.
- Configure log rotation.
- Deploy environment files.
- Create service users.
- Roll out config changes across hosts.
- Verify host health before deployment.

### Production Mistakes

- Running playbooks against the wrong inventory.
- Restarting all hosts at once.
- Storing secrets in plaintext variables.
- Not using `--check --diff` before sensitive changes.
- Writing non-idempotent shell tasks.
- Ignoring failure strategy for rolling deploys.

Rolling pattern:

```yaml
- name: Rolling deploy
  hosts: order_routers
  serial: 1
  become: true
```

This updates one host at a time.

## Interview Questions

- "Why use containers for backend services?"
  - Answer: Containers package runtime dependencies and make deployments more repeatable, but still need correct networking, secrets, resource limits, and monitoring.
- "Why can a container be running but the service unreachable?"
  - Answer: The app may bind to `127.0.0.1`, the port may not be published, health checks may fail, firewall rules may block traffic, or dependencies may be missing.
- "Difference between image and container?"
  - Answer: An image is the immutable package/template; a container is a running instance of that image with runtime state.
- "How do you inspect container logs?"
  - Answer: Use `docker logs`, service/orchestrator logs, and structured app logs; correlate with timestamps and container IDs.
- "What should not be put in a Docker image?"
  - Answer: Do not bake secrets, private keys, production credentials, or environment-specific config into Docker images.
- "How does Ansible reduce production drift?"
  - Answer: It declares host state in versioned playbooks and applies the same configuration repeatedly across hosts.
- "Why should Ansible tasks be idempotent?"
  - Answer: Idempotent tasks are safe to rerun; they change the host only when desired state differs from actual state.

Warning: Docker improves packaging consistency, but production still needs correct networking, secrets, host limits, and observability.

## Quick Revision

- Image is the package; container is the running instance.
- `docker logs`, `docker exec`, `docker inspect`, and `docker stats` are core debugging commands.
- Publish ports with `host:container`, and bind apps to `0.0.0.0` inside containers.
- Use volumes for persistent data/config, but protect secrets.
- Ansible automates host state over SSH using inventories and playbooks.
- Use rolling deploys and dry runs for production infrastructure changes.
