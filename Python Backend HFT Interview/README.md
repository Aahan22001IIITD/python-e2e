# Python Backend/HFT Systems Interview Notes

Tags: #python #backend #hft #systems #interview

Role focus: Python services, exchange connectors, APIs, automation, Linux workflows, monitoring, reliability, concurrency, performance tuning, and distributed backend systems.

Use this as a quick-revision map:

## Backend Systems / Python Infrastructure / HFT

- [[Backend Systems Index]] — Obsidian map for backend systems, Python infrastructure, HFT production, and final interview revision
- [[04 Backend Systems/01 APIs HTTP and Web Frameworks]] — REST, HTTP methods, status codes, FastAPI/Flask, API design, middleware, authentication
- [[04 Backend Systems/02 Observability Reliability and Traffic Control]] — logging, monitoring, retries, timeouts, rate limiting, incident debugging
- [[04 Backend Systems/03 Data Caching and Persistence]] — connection pooling, caching, Redis, indexing, joins, transactions
- [[04 Backend Systems/04 Concurrency Distributed Systems and Scaling]] — concurrency, queues/workers, distributed systems, idempotency, horizontal scaling, load balancing
- [[05 HFT Production Engineering/Exchange Connectivity Linux and Automation]] — exchange connectivity, real-time systems, Linux production debugging, infrastructure automation
- [[06 Backend Interview Revision/Backend Systems Final Revision]] — top interview questions, one-hour revision, mistakes, HFT tips, exercises, debugging and design scenarios

## 01 Python Core

- [[01 Python Core/Core object semantics]] — mutability, copy behavior, identity/equality, list vs tuple, set vs dict
- [[01 Python Core/Collections and counting patterns]] — `defaultdict`, `deque`, `Counter`, backend use cases
- [[01 Python Core/Python Core interview question answers]] — answer key for Python Core interview questions and traps

## 02 Runtime Patterns

- [[02 Runtime Patterns/Comprehensions functional tools and iteration]] — comprehensions, generator expressions, `lambda`, `map`, `filter`, iterators, generators
- [[02 Runtime Patterns/Decorators context managers and exceptions]] — production wrappers, resource safety, retries, logging
- [[02 Runtime Patterns/Functions classes and architecture]] — `*args`, `**kwargs`, class methods, static methods, inheritance, polymorphism, composition
- [[02 Runtime Patterns/Concurrency GIL async and multiprocessing]] — threading, multiprocessing, GIL, `async`/`await`, backend concurrency choices
- [[02 Runtime Patterns/File and JSON handling]] — streaming files, parsing APIs, safe serialization

## 03 Production Revision

- [[03 Production Revision/Interview question bank]]
- [[03 Production Revision/Interview question bank solutions]]
- [[03 Production Revision/One hour revision]]
- [[03 Production Revision/Coding exercises]]

## 05 HFT Production Engineering

- [[05 HFT Production Engineering/Trading Systems and Exchange Infrastructure/00 Index]] — order lifecycle, exchange connectivity, websockets, latency, reliability, and trading backend interview revision

## 07 Linux Infra Monitoring Reliability

- [[07 Linux Infra Monitoring Reliability/00 Index]] — Linux, infrastructure, monitoring, reliability, and incident-response revision map
- [[07 Linux Infra Monitoring Reliability/01 Shell Scripting and Text Processing]] — bash, `grep`, `awk`, `sed`, log processing, automation examples
- [[07 Linux Infra Monitoring Reliability/02 Permissions Environment and Scheduling]] — `chmod`, env vars, secrets/config handling, cron jobs
- [[07 Linux Infra Monitoring Reliability/03 Processes Services and Network Debugging]] — `ps`, `top`, `ss`, `netstat`, `lsof`, `systemctl`, production host debugging
- [[07 Linux Infra Monitoring Reliability/04 SSH Logs and Production Access]] — SSH, SCP, secure access, structured logs, incident tracing
- [[07 Linux Infra Monitoring Reliability/05 Docker and Ansible Basics]] — Dockerfiles, containers, compose, production debugging, Ansible automation
- [[07 Linux Infra Monitoring Reliability/06 Monitoring Prometheus Grafana and Alerting]] — Prometheus, scraping, exporters, PromQL, Grafana dashboards, metrics vs logs, alerting
- [[07 Linux Infra Monitoring Reliability/07 Reliability Health Checks Retries and Incidents]] — uptime, SLOs, liveness/readiness, retries, circuit breakers, fault tolerance
- [[07 Linux Infra Monitoring Reliability/08 Revision Bank Scenarios and Commands]] — interview questions, outage workflows, backend failure fixes, Prometheus/Grafana revision, HFT scenarios

## How to answer in interviews

For most Python backend questions, answer in this order:

1. Define the concept precisely.
2. Explain object ownership / references / lifecycle.
3. Give the backend failure mode.
4. Mention performance or concurrency tradeoff.
5. Show the safe production pattern.

Example:

```python
def answer_pattern():
    return [
        "what it is",
        "why it matters in memory/reference behavior",
        "production bug it prevents",
        "performance tradeoff",
        "safe code pattern",
    ]
```
