# Backend Systems / Python Infrastructure / HFT Interview

Tags: #backend #python #hft #systems #interview #reliability #infrastructure

Role focus: Python backend services, exchange connectivity, APIs, distributed systems, monitoring, Linux production environments, reliability engineering, infrastructure automation, and performance-sensitive real-time systems.

Use this note for fast interview revision. Prefer production examples over textbook definitions. In answers, explain the failure mode, the tradeoff, and how you would operate it in production.

---

## How To Answer Backend Interview Questions

For most topics, answer in this order:

1. What the concept is.
2. Why it matters in backend systems.
3. What breaks in production.
4. How you design, debug, and operate it.
5. What performance or reliability tradeoff you are making.

Backend interviewers usually care less about memorized definitions and more about whether you can prevent incidents.

Example answer shape:

```text
For an order-placement API, I care about idempotency because clients may retry after timeouts.
I would accept an Idempotency-Key, persist request state, return the original result on duplicate retries,
set a TTL, and make the database write atomic with a unique constraint.
The trap is treating retries as harmless when the downstream exchange may already have accepted the order.
```

---

# Backend + Systems

## REST APIs

### Concept

REST APIs expose resources through URLs and standard HTTP semantics. A backend should model business entities as resources, keep requests stateless, and use predictable request/response behavior.

Good resource examples:

- `/orders/{order_id}`
- `/accounts/{account_id}/positions`
- `/exchange-connections/{venue}/status`

Bad examples:

- `/doOrderThing`
- `/getData`
- `/api/process`

### Why It Matters In Backend Systems

REST gives clients, load balancers, gateways, caches, monitoring, and debuggers a shared contract. In trading/internal ops systems, this matters because APIs become operational boundaries between services, dashboards, workers, and exchange connectors.

### Production Relevance

Production APIs need:

- Stateless handlers so requests can hit any instance.
- Clear error models so clients can react safely.
- Idempotency for retryable writes.
- Pagination for large datasets.
- Compatibility across deployed client versions.
- Observability through request IDs and structured logs.

### Request Lifecycle

```text
client -> DNS -> load balancer -> gateway/proxy -> app middleware -> route handler
       -> validation -> authz -> business logic -> DB/cache/downstream service
       -> response serialization -> logs/metrics/traces -> client
```

### FastAPI Example

```python
from fastapi import FastAPI, Query, Request
from pydantic import BaseModel

app = FastAPI()

class OrderOut(BaseModel):
    id: str
    symbol: str
    side: str
    quantity: int
    status: str

@app.get("/v1/orders", response_model=list[OrderOut])
async def list_orders(
    request: Request,
    account_id: str,
    limit: int = Query(default=100, le=500),
    cursor: str | None = None,
    status: str | None = None,
):
    # In production, use cursor pagination instead of OFFSET for large tables.
    request_id = request.headers.get("x-request-id")
    return await fetch_orders(account_id, limit=limit, cursor=cursor, status=status, request_id=request_id)
```

### API Versioning

| Strategy | Usage | Tradeoff |
|---|---|---|
| `/v1/orders` | Common and explicit | URL clutter, but easy to operate |
| Header versioning | `Accept: application/vnd.app.v2+json` | Cleaner URLs, harder debugging |
| Backward-compatible evolution | Add optional fields only | Best default, but requires discipline |

Breaking changes require a new version. Adding response fields is usually safe. Removing or renaming fields is not.

### Pagination, Filtering, Sorting

Use cursor pagination for changing data:

```sql
SELECT id, symbol, created_at
FROM orders
WHERE account_id = :account_id
  AND created_at < :cursor_created_at
ORDER BY created_at DESC, id DESC
LIMIT :limit;
```

Avoid `OFFSET` on large tables because the database still scans skipped rows.

### Interview Traps

- Saying REST means "JSON over HTTP" only.
- Using `POST` for every operation.
- Returning `200 OK` for all errors.
- Forgetting idempotency on write APIs.
- Designing list endpoints with no pagination.
- Making server-side sessions mandatory for horizontally scaled APIs.

### Performance Considerations

- Avoid N+1 database queries in list endpoints.
- Put limits on payload size and page size.
- Compress large responses when useful.
- Do not log full large payloads or secrets.
- Use connection pools for DB and downstream HTTP calls.

### Scalability And Reliability

- Stateless services scale horizontally.
- Idempotent write APIs tolerate retries.
- Clear status codes improve client fallback behavior.
- Versioned APIs prevent lockstep deployments.

### Common Mistakes

- Mixing transport errors, validation errors, and business errors.
- Exposing internal database IDs where public IDs are safer.
- Leaking implementation details in error messages.
- Using unstable sorting, causing duplicate/missing paginated results.

### Quick Revision

- REST is resource-oriented HTTP with predictable semantics.
- Statelessness enables load balancing and horizontal scaling.
- Pagination, idempotency, validation, and observability are production requirements.

---

## HTTP Methods

### Concept

HTTP methods describe client intent. Correct method choice improves safety, caching, retry behavior, and debugging.

| Method | Safe | Idempotent | Typical Backend Use |
|---|---:|---:|---|
| `GET` | Yes | Yes | Read resource |
| `POST` | No | No by default | Create action or command |
| `PUT` | No | Yes | Replace resource |
| `PATCH` | No | Usually no | Partial update |
| `DELETE` | No | Yes | Delete/cancel resource |

Safe means no state change. Idempotent means repeating the same request has the same final effect.

### Production Examples

```python
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()

@app.post("/v1/orders")
async def create_order(order: dict, idempotency_key: str = Header(alias="Idempotency-Key")):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key required")
    return await create_order_once(order, idempotency_key)

@app.delete("/v1/orders/{order_id}")
async def cancel_order(order_id: str):
    # Repeating this should not create a second cancel side effect.
    return await cancel_order_idempotently(order_id)
```

### Backend Usage Patterns

- `GET /orders/{id}` reads an order.
- `POST /orders` creates an order.
- `PUT /risk-limits/{account_id}` replaces a full risk limit config.
- `PATCH /orders/{id}` updates mutable metadata, not usually exchange state.
- `DELETE /orders/{id}` often means cancel, not physically delete.

### Interview Traps

- "POST is always create" is too simplistic. It can represent commands like `/orders/{id}/cancel`.
- `DELETE` can be idempotent even if the first call deletes and the second returns `404` or `204`.
- `PATCH` needs careful merge semantics.

### Performance Considerations

- `GET` can be cached if auth and freshness allow.
- Large `PUT` payloads may waste bandwidth.
- `PATCH` can reduce payload size but complicates validation.

### Scalability And Reliability

- Correct idempotency lets gateways, clients, and workers retry safely.
- Safe methods should not mutate state, or crawlers/monitors can cause incidents.

### Common Mistakes

- Triggering side effects from `GET`.
- Using `POST` for reads because filters are complex.
- Treating retry of `POST` as safe without an idempotency key.

### Quick Revision

- `GET` is safe and idempotent.
- `POST` is not idempotent unless you design it to be.
- `PUT` replaces, `PATCH` partially updates, `DELETE` should be retry-safe.

---

## Status Codes

### Concept

HTTP status codes communicate the outcome class. They matter because clients, retries, dashboards, and alerts often depend on them.

| Class | Meaning | Backend Interpretation |
|---|---|---|
| `2xx` | Success | Request completed |
| `3xx` | Redirect/cache flow | Usually handled by clients/proxies |
| `4xx` | Client-side problem | Bad input, auth, missing resource |
| `5xx` | Server-side problem | Dependency failure, bug, overload |

### Practical API Usage

```python
from fastapi import HTTPException

def map_order_error(error: Exception):
    if isinstance(error, ValidationError):
        raise HTTPException(400, "Invalid order request")
    if isinstance(error, Unauthorized):
        raise HTTPException(401, "Authentication required")
    if isinstance(error, Forbidden):
        raise HTTPException(403, "Insufficient permissions")
    if isinstance(error, OrderNotFound):
        raise HTTPException(404, "Order not found")
    if isinstance(error, DuplicateRequest):
        raise HTTPException(409, "Duplicate idempotency key")
    if isinstance(error, DownstreamTimeout):
        raise HTTPException(503, "Exchange gateway unavailable")
    raise HTTPException(500, "Internal server error")
```

### Common Codes

| Code | Use |
|---:|---|
| `200` | Successful read/update |
| `201` | Resource created |
| `202` | Accepted for async processing |
| `204` | Success with no body |
| `400` | Invalid request |
| `401` | Not authenticated |
| `403` | Authenticated but not allowed |
| `404` | Resource not found |
| `409` | Conflict, duplicate, state mismatch |
| `422` | Semantic validation failure, common in FastAPI |
| `429` | Rate limited |
| `500` | Unexpected server bug |
| `502` | Bad upstream response |
| `503` | Temporarily unavailable |
| `504` | Upstream timeout |

### Debugging Relevance

- Spike in `400`: client bug, schema mismatch, bad deployment.
- Spike in `401/403`: auth config or token expiry issue.
- Spike in `409`: concurrency/idempotency conflict.
- Spike in `429`: abuse, traffic burst, or too strict limits.
- Spike in `5xx`: server/dependency incident.

### Interview Traps

- Returning `500` for validation errors.
- Returning `200` with `{ "success": false }`.
- Confusing `401` and `403`.
- Using `404` to hide all authorization failures without consistency.

### Performance Considerations

- Avoid expensive work before validation/auth.
- Separate 4xx from 5xx in SLO metrics.
- High-cardinality error labels can damage metrics systems.

### Scalability And Reliability

- Status codes drive retry policy.
- `5xx` can trigger alerts and autoscaling.
- `429` protects systems under load.

### Quick Revision

- `4xx` means the client likely must change something.
- `5xx` means retry may help, depending on method/idempotency.
- Use `409` for state conflicts and `429` for rate limits.

---

## FastAPI / Flask Basics

### Concept

FastAPI and Flask are Python web frameworks for building backend APIs. Flask is minimal and flexible. FastAPI provides type-driven validation, OpenAPI generation, dependency injection, and first-class async support.

| Area | FastAPI | Flask |
|---|---|---|
| Validation | Built-in with Pydantic | Add Marshmallow/Pydantic manually |
| Async | Native ASGI | Historically WSGI, async support limited by stack |
| Docs | Automatic OpenAPI | Extension/manual |
| Style | Typed, declarative | Minimal, explicit |
| Best fit | API services | Small apps, custom/simple services |

### Routing And Validation

```python
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

app = FastAPI()

class RiskLimitUpdate(BaseModel):
    max_notional_usd: float = Field(gt=0)
    max_order_qty: int = Field(gt=0)

async def current_user():
    return {"user_id": "u123", "role": "ops"}

@app.put("/v1/accounts/{account_id}/risk-limit")
async def update_risk_limit(
    account_id: str,
    payload: RiskLimitUpdate,
    user: dict = Depends(current_user),
):
    return await save_risk_limit(account_id, payload, updated_by=user["user_id"])
```

Flask equivalent:

```python
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/v1/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})
```

### Middleware

```python
import time
import uuid
from fastapi import Request

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    response.headers["x-latency-ms"] = str(round((time.perf_counter() - start) * 1000, 2))
    return response
```

### Production Deployment

- Run FastAPI with ASGI servers like `uvicorn` behind `gunicorn` or a process manager.
- Use multiple workers for CPU-bound request handling.
- Set timeouts at app, worker, proxy, and load balancer layers.
- Gracefully handle shutdown so in-flight requests complete.
- Keep secrets and config in environment/config management, not code.

### Interview Traps

- Thinking `async def` automatically makes code faster.
- Calling blocking DB/HTTP clients inside async handlers.
- Running development servers in production.
- No request validation or schema contracts.

### Performance Considerations

- Async helps I/O-bound concurrency, not CPU-heavy work.
- Use connection pools for DB and HTTP clients.
- Keep Pydantic models reasonable on hot paths.
- Avoid per-request expensive initialization.

### Scalability And Reliability

- FastAPI fits typed API services and internal platforms.
- Flask is fine when you intentionally assemble the stack.
- Either framework needs production-grade deployment, logging, metrics, and timeouts.

### Quick Revision

- FastAPI: validation, OpenAPI, DI, async.
- Flask: minimal, flexible, extension-based.
- Framework choice matters less than production discipline.

---

## API Design

### Concept

API design is about stable contracts. A clean API is predictable, versioned, observable, and hard to misuse.

### Production Principles

- Use nouns for resources: `/orders`, `/positions`.
- Keep naming consistent: `account_id`, not mixed `accountId`.
- Use stable response envelopes for errors.
- Add optional fields instead of breaking existing clients.
- Make dangerous actions explicit.
- Design for retries, pagination, and partial failures.

### Error Response Design

```json
{
  "error": {
    "code": "ORDER_REJECTED_BY_RISK",
    "message": "Order exceeds max notional limit",
    "request_id": "req-123",
    "details": {
      "limit": 100000,
      "requested": 150000
    }
  }
}
```

### Backend Example

```python
from fastapi import Request
from fastapi.responses import JSONResponse

class DomainError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message

@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request.headers.get("x-request-id"),
            }
        },
    )
```

### Scalability Concerns

- Avoid endpoints that return unbounded datasets.
- Avoid chatty APIs when one request could safely return needed data.
- Avoid huge aggregate endpoints that couple many backend services.
- Use async workflows for long-running operations.

### Interview Traps

- No answer for backward compatibility.
- No error schema.
- No pagination.
- No idempotency for creates.
- No plan for client migrations.

### Performance Considerations

- Stable filters need indexes.
- Consistent sort order improves pagination correctness.
- Large response payloads increase latency and memory pressure.

### Common Mistakes

- Mirroring database tables directly as public API.
- Returning internal exception text.
- Using inconsistent timestamp formats.
- Making all fields nullable because the domain is unclear.

### Quick Revision

- APIs are contracts, not just handlers.
- Compatibility beats short-term convenience.
- Design failure responses as carefully as success responses.

---

## Middleware Concept

### Concept

Middleware wraps request processing. It runs before and/or after route handlers and is ideal for cross-cutting concerns.

Common middleware:

- Authentication
- Request ID propagation
- Logging
- Metrics
- Rate limiting
- CORS
- Compression

### Request Lifecycle

```text
request -> middleware A -> middleware B -> route handler -> middleware B -> middleware A -> response
```

### Logging Middleware Example

```python
import logging
import time

logger = logging.getLogger("api")

@app.middleware("http")
async def access_log_middleware(request, call_next):
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request_completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "latency_ms": round(elapsed_ms, 2),
                "request_id": request.headers.get("x-request-id"),
            },
        )
```

### Production Relevance

Middleware makes observability and security consistent. Without it, each handler implements logging/auth/rate limiting differently, which causes gaps during incidents.

### Interview Traps

- Doing heavy blocking work in middleware.
- Logging sensitive headers.
- Swallowing exceptions and returning fake success.
- Incorrect middleware ordering.

### Performance Considerations

- Middleware runs on every request.
- Keep it small and predictable.
- Avoid synchronous network calls.
- Sample expensive logging/tracing if traffic is high.

### Scalability And Reliability

- Request IDs enable cross-service debugging.
- Central auth middleware reduces inconsistent access control.
- Rate limiting middleware protects downstream dependencies.

### Quick Revision

- Middleware handles cross-cutting request concerns.
- It is powerful because it runs everywhere.
- Bad middleware can slow or break every endpoint.

---

## Authentication Basics

### Concept

Authentication verifies identity. Authorization decides what the identity can do.

| Mechanism | Best Use | Production Caveat |
|---|---|---|
| Sessions | Browser apps | Needs shared store or sticky sessions |
| JWT | Stateless service auth | Revocation is harder |
| API keys | Service/internal clients | Rotation and scope management matter |
| OAuth | Delegated access | More moving parts and token flows |

### JWT Example

```python
from fastapi import Depends, Header, HTTPException

async def require_api_key(x_api_key: str = Header(alias="X-API-Key")):
    client = await lookup_api_client(x_api_key)
    if not client:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if not client.enabled:
        raise HTTPException(status_code=403, detail="Client disabled")
    return client

@app.post("/v1/internal/reconcile")
async def reconcile(client=Depends(require_api_key)):
    return await start_reconciliation(client_id=client.id)
```

### Token Expiration

- Short-lived access tokens reduce exposure.
- Refresh tokens need secure storage.
- API keys need rotation, ownership, audit logs, and scopes.
- Expired tokens should return `401`, not `500`.

### Production Pitfalls

- No key rotation path.
- Long-lived tokens with broad permissions.
- Auth result cached too long after user/client disabled.
- Logging tokens accidentally.
- Confusing authentication failure with authorization denial.

### Interview Traps

- Saying JWT is always better because it is stateless.
- Ignoring revocation.
- Ignoring clock skew on token expiry.
- No answer for service-to-service auth.

### Performance Considerations

- Local JWT verification is fast.
- DB lookup on every request can bottleneck unless cached carefully.
- Authorization checks may need indexed permission tables.

### Scalability And Reliability

- Stateless auth scales easily but complicates revocation.
- Central auth services simplify policy but can become critical dependencies.
- Cache auth decisions with short TTL and clear invalidation strategy.

### Quick Revision

- Authentication is identity; authorization is permission.
- JWT trades revocation complexity for stateless validation.
- API keys require scopes, rotation, and auditability.

---

## Logging Systems

### Concept

Logging records discrete events. Production logging should be structured, searchable, correlated, and safe.

### Structured Logging Example

```python
import logging

logger = logging.getLogger("orders")

def log_order_rejected(order_id: str, account_id: str, reason: str, request_id: str):
    logger.warning(
        "order_rejected",
        extra={
            "order_id": order_id,
            "account_id": account_id,
            "reason": reason,
            "request_id": request_id,
        },
    )
```

### Log Levels

| Level | Use |
|---|---|
| `DEBUG` | Local diagnostics, usually off in prod |
| `INFO` | Important lifecycle events |
| `WARNING` | Unexpected but handled |
| `ERROR` | Failed operation needing attention |
| `CRITICAL` | Severe system-level failure |

### Production Relevance

During incidents, logs answer:

- What request failed?
- Which user/account/order was affected?
- Which dependency failed?
- Was this a validation issue, timeout, or bug?
- Did retries happen?

### Correlation IDs

Propagate `x-request-id` across services, logs, traces, and responses.

```python
headers = {"x-request-id": request_id}
response = await http_client.post(exchange_url, json=payload, headers=headers)
```

### Interview Traps

- Logging only exception strings without context.
- Logging secrets, tokens, PII, or full order payloads.
- Using logs as metrics.
- No correlation ID.

### Performance Considerations

- Excessive logging increases latency and storage cost.
- Synchronous remote logging can block request handling.
- High-cardinality fields are okay in logs but dangerous in metrics.

### Scalability And Reliability

- Centralized logs support multi-instance debugging.
- Sampling may be needed for very high throughput.
- Logs should survive app restarts and container churn.

### Quick Revision

- Logs are event records, not counters.
- Use structured logs with request IDs.
- Never log secrets.

---

## Monitoring Basics

### Concept

Monitoring observes system health. Observability usually combines metrics, logs, and traces.

| Signal | Answers |
|---|---|
| Metrics | How often? How slow? How many? |
| Logs | What happened in this event? |
| Traces | Where did time go across services? |

### Production Metrics

Track RED metrics for APIs:

- Rate: requests per second.
- Errors: failed requests by class.
- Duration: latency percentiles.

Track USE metrics for infrastructure:

- Utilization.
- Saturation.
- Errors.

### Health Check Example

```python
@app.get("/health/live")
async def live():
    return {"status": "alive"}

@app.get("/health/ready")
async def ready():
    db_ok = await check_db()
    redis_ok = await check_redis()
    if not db_ok or not redis_ok:
        raise HTTPException(status_code=503, detail="Not ready")
    return {"status": "ready"}
```

### Prometheus Metric Example

```python
from prometheus_client import Counter, Histogram

ORDERS_CREATED = Counter("orders_created_total", "Orders created", ["venue"])
ORDER_LATENCY = Histogram("order_create_latency_seconds", "Order create latency")

async def create_order_handler(order):
    with ORDER_LATENCY.time():
        result = await submit_order(order)
    ORDERS_CREATED.labels(venue=order.venue).inc()
    return result
```

### Alerting

Good alerts are actionable:

- High 5xx rate for 5 minutes.
- p99 latency above SLO.
- Queue lag increasing.
- Exchange disconnect.
- Database pool exhaustion.

Bad alerts:

- CPU above 60% once.
- Every single exception.
- No runbook.

### Interview Traps

- Confusing liveness and readiness checks.
- Alerting on symptoms with no action.
- Ignoring latency percentiles.
- Measuring only averages.

### Performance Considerations

- Avoid high-cardinality labels like `user_id` or `order_id`.
- Metrics collection should be low overhead.
- Histograms need carefully chosen buckets.

### Scalability And Reliability

- Monitoring detects failures before users report them.
- Readiness checks prevent broken instances receiving traffic.
- SLOs align engineering work with user impact.

### Quick Revision

- Metrics for trends, logs for details, traces for paths.
- Alert on user impact and saturation.
- Use p95/p99, not only averages.

---

## Retries And Timeouts

### Concept

Distributed calls fail. Timeouts bound waiting. Retries recover from transient failures. Bad retries can amplify outages.

### Production Pattern

```python
import random
import httpx

async def post_with_retry(url: str, payload: dict, request_id: str):
    timeout = httpx.Timeout(connect=0.5, read=2.0, write=0.5, pool=0.5)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(3):
            try:
                return await client.post(url, json=payload, headers={"x-request-id": request_id})
            except (httpx.ConnectTimeout, httpx.ReadTimeout):
                if attempt == 2:
                    raise
                backoff = min(0.05 * (2 ** attempt), 0.5)
                jitter = random.uniform(0, backoff)
                await asyncio.sleep(jitter)
```

### Backend Relevance

APIs call databases, Redis, exchanges, internal services, object stores, and queues. Without timeouts, threads/workers can hang until the service is effectively down.

### Retry Strategy

- Retry only transient failures.
- Use exponential backoff with jitter.
- Set a retry budget.
- Make write operations idempotent before retrying.
- Respect downstream rate limits.

### Interview Traps

- Retrying all errors including `400`.
- Infinite retries.
- No timeout.
- Retrying non-idempotent writes.
- Every service layer retrying and multiplying traffic.

### Performance Considerations

- Timeouts should be shorter than client timeouts.
- Retries increase tail latency.
- Retry storms can overload recovering services.

### Scalability And Reliability

- Timeouts preserve worker capacity.
- Circuit breakers can stop repeated calls to failing dependencies.
- Bulkheads isolate failures by dependency or tenant.

### Quick Revision

- Always set timeouts.
- Retry with backoff and jitter.
- Never retry unsafe writes without idempotency.

---

## Rate Limiting

### Concept

Rate limiting controls how many requests a client, account, IP, or service can make in a time period.

### Algorithms

| Algorithm | Behavior | Tradeoff |
|---|---|---|
| Fixed window | Count per time bucket | Simple but boundary bursts |
| Sliding window | Rolling time range | More accurate, more storage |
| Token bucket | Tokens refill over time | Allows controlled bursts |
| Leaky bucket | Smooth output rate | Good for steady downstream protection |

### Redis Token Bucket Example

```python
import time

async def allow_request(redis, key: str, rate_per_sec: int, burst: int) -> bool:
    now = time.time()
    bucket = await redis.hgetall(key)
    tokens = float(bucket.get("tokens", burst))
    updated_at = float(bucket.get("updated_at", now))

    tokens = min(burst, tokens + (now - updated_at) * rate_per_sec)
    if tokens < 1:
        await redis.hset(key, mapping={"tokens": tokens, "updated_at": now})
        return False

    await redis.hset(key, mapping={"tokens": tokens - 1, "updated_at": now})
    await redis.expire(key, 60)
    return True
```

In production, use a Lua script for atomicity.

### Production Relevance

Rate limiting protects:

- Public APIs from abuse.
- Internal services from accidental floods.
- Exchange gateways from venue limits.
- Expensive endpoints from noisy tenants.

### Interview Traps

- Only rate limiting by IP behind NAT.
- Non-atomic distributed counters.
- Returning `500` instead of `429`.
- No `Retry-After` hint.

### Performance Considerations

- Redis round trip on every request can be expensive.
- Local limits are fast but inaccurate across instances.
- High-cardinality rate limit keys increase memory use.

### Scalability And Reliability

- Distributed rate limits need shared state or approximate local budgets.
- Fail-open protects availability but risks overload.
- Fail-closed protects dependencies but can block valid traffic.

### Quick Revision

- Use `429` for rate limits.
- Token bucket supports bursts.
- Distributed rate limiting needs atomic shared state.

---

## Connection Pooling

### Concept

Connection pooling reuses expensive connections to databases, Redis, and HTTP services.

### Why It Matters

Opening TCP/TLS/database connections per request is slow and can exhaust servers. Pools improve latency and protect backends by bounding concurrency.

### Database Pool Example

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    "postgresql+asyncpg://app:secret@db:5432/trading",
    pool_size=10,
    max_overflow=20,
    pool_timeout=1,
    pool_recycle=1800,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_session():
    async with SessionLocal() as session:
        yield session
```

### HTTP Pool Example

```python
import httpx

http_client = httpx.AsyncClient(
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
    timeout=httpx.Timeout(2.0),
)
```

### Production Pitfalls

- Pool size larger than database can handle.
- Creating a new client/session per request.
- Not closing sessions.
- No pool timeout, causing request pileups.

### Interview Traps

- Thinking bigger pool is always better.
- Forgetting each app instance has its own pool.
- Ignoring worker count times pool size.

### Performance Considerations

- Pool too small: queueing and latency.
- Pool too large: DB overload and context switching.
- Keepalive improves HTTP latency.

### Scalability And Reliability

- Pools provide backpressure.
- Pool exhaustion is often an early incident signal.
- Database capacity must consider total app replicas.

### Quick Revision

- Reuse connections.
- Bound concurrency.
- Size pools based on total replicas and DB capacity.

---

## Caching Basics

### Concept

Caching stores computed or fetched data closer to the caller to reduce latency, database load, or downstream calls.

### Patterns

| Pattern | Flow | Use |
|---|---|---|
| Cache-aside | App reads/writes cache explicitly | Common backend default |
| Read-through | Cache loads missing data | Cleaner app code, cache-specific |
| Write-through | Write cache and DB together | Stronger freshness, slower writes |
| Write-behind | Write cache first, DB later | Fast but riskier |

### Cache-Aside Example

```python
import json

async def get_account_limits(redis, db, account_id: str):
    key = f"risk_limit:{account_id}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)

    limits = await db.fetch_account_limits(account_id)
    await redis.set(key, json.dumps(limits), ex=30)
    return limits
```

### Production Relevance

Caching helps:

- Frequently read reference data.
- Risk limits and account configs with short TTL.
- Expensive aggregations.
- API response acceleration.

### Cache Invalidation

Hardest part:

- Use TTL for bounded staleness.
- Invalidate on writes when correctness requires it.
- Version cache keys for schema changes.
- Prevent thundering herds with locks or request coalescing.

### Interview Traps

- Ignoring stale data.
- Caching errors forever.
- No TTL.
- Cache key missing tenant/account dimension.
- No plan for cache warmup or outage.

### Performance Considerations

- Serialization cost matters on hot paths.
- Large values increase network and memory pressure.
- Cache hit ratio is more useful than just cache presence.

### Scalability And Reliability

- Cache failure should usually degrade, not take down the system.
- Avoid making Redis a single point of failure for non-critical reads.
- Critical correctness paths may not tolerate stale cache.

### Quick Revision

- Cache for latency and load reduction.
- TTL bounds staleness.
- Invalidation and key design are the hard parts.

---

## Redis Basics

### Concept

Redis is an in-memory data store used for caching, counters, queues, pub/sub, locks, and rate limiting.

### Common Backend Uses

| Use | Redis Data Structure |
|---|---|
| Cache | String/hash with TTL |
| Rate limit | Counter/token bucket |
| Queue | List/stream |
| Pub/sub | Channel |
| Leader/lock | Key with TTL |
| Deduplication | Set |

### Examples

Cache:

```python
await redis.set("market_status:NASDAQ", "open", ex=5)
status = await redis.get("market_status:NASDAQ")
```

Queue:

```python
await redis.lpush("order_events", json.dumps(event))
event = await redis.brpop("order_events", timeout=5)
```

Distributed lock:

```python
lock_acquired = await redis.set("lock:reconcile:AAPL", "worker-7", nx=True, ex=30)
if lock_acquired:
    try:
        await reconcile_symbol("AAPL")
    finally:
        await release_lock_safely(redis, "lock:reconcile:AAPL", "worker-7")
```

Use a compare-and-delete Lua script for safe lock release.

### Production Pitfalls

- Assuming Redis is durable by default.
- No TTL on temporary keys.
- Huge keys or unbounded lists.
- Using pub/sub when consumers need durable delivery.
- Unsafe distributed locks.

### Interview Traps

- Calling Redis "just a cache".
- Ignoring memory eviction policy.
- No answer for Redis outage.
- Using Redis locks for correctness-critical financial state without careful fencing.

### Performance Considerations

- Redis is fast but single-threaded for command execution.
- Network round trips dominate many small operations.
- Use pipelining or Lua for atomic multi-step operations.

### Scalability And Reliability

- Redis Cluster helps scale keyspace but adds operational complexity.
- Sentinel/managed failover improves availability.
- For durable streams/jobs, consider Redis Streams, Kafka, RabbitMQ, or database-backed queues depending on guarantees.

### Quick Revision

- Redis is in-memory and fast.
- TTLs, memory policy, and durability matter.
- Use atomic operations for counters, locks, and rate limits.

---

## Database Indexing

### Concept

Indexes are data structures that help the database find rows without scanning the whole table. Most relational databases use B-tree indexes for equality and range queries.

### B-Tree Intuition

B-trees keep sorted keys and pointers to rows. They are good for:

- Equality: `account_id = ?`
- Range: `created_at >= ?`
- Sorting: `ORDER BY created_at`
- Prefix of composite indexes.

### Practical Example

```sql
CREATE INDEX idx_orders_account_created
ON orders (account_id, created_at DESC, id DESC);

SELECT id, symbol, status, created_at
FROM orders
WHERE account_id = 'acct_123'
ORDER BY created_at DESC, id DESC
LIMIT 100;
```

### Production Relevance

Indexes prevent slow queries from becoming incidents. In trading backends, slow queries can delay dashboards, risk checks, reconciliation, or order workflows.

### Tradeoffs

| Benefit | Cost |
|---|---|
| Faster reads | Slower writes |
| Faster filtering/sorting | More disk/memory |
| Unique constraints | More lock/contention risk |

### Slow Query Debugging

```sql
EXPLAIN ANALYZE
SELECT *
FROM fills
WHERE account_id = 'acct_123'
  AND symbol = 'AAPL'
  AND executed_at >= now() - interval '1 day';
```

Look for sequential scans, bad row estimates, missing indexes, and large sorts.

### Interview Traps

- Indexing every column.
- Wrong composite index order.
- Not understanding that functions can prevent index use.
- Using `SELECT *` on wide rows.

### Performance Considerations

- Composite indexes work left to right.
- Low-cardinality columns alone often make weak indexes.
- Covering indexes can avoid table lookups.
- Indexes need maintenance and statistics.

### Scalability And Reliability

- Missing indexes can overload the DB under traffic spikes.
- Too many indexes slow writes and migrations.
- Unique indexes are excellent for idempotency and consistency.

### Quick Revision

- Index for query patterns, not columns.
- Composite index order matters.
- Indexes speed reads but tax writes.

---

## SQL Joins

### Concept

Joins combine rows from related tables. Backend engineers need joins to fetch normalized data without excessive application-side queries.

### Join Types

| Join | Meaning |
|---|---|
| `INNER JOIN` | Rows matching in both tables |
| `LEFT JOIN` | All left rows plus matches from right |
| `RIGHT JOIN` | All right rows plus matches from left |
| `FULL JOIN` | All rows from both sides |

### Practical Examples

```sql
-- Orders with account metadata.
SELECT o.id, o.symbol, o.quantity, a.name AS account_name
FROM orders o
INNER JOIN accounts a ON a.id = o.account_id
WHERE o.status = 'OPEN';
```

```sql
-- Accounts even if they have no open orders.
SELECT a.id, a.name, COUNT(o.id) AS open_order_count
FROM accounts a
LEFT JOIN orders o
  ON o.account_id = a.id
 AND o.status = 'OPEN'
GROUP BY a.id, a.name;
```

### Backend Relevance

Correct joins prevent N+1 queries and inconsistent application-side stitching.

### Interview Traps

- Filtering a `LEFT JOIN` table in `WHERE`, accidentally turning it into an `INNER JOIN`.
- Joining on non-indexed columns.
- Not handling duplicate rows from one-to-many relationships.

### Performance Considerations

- Join keys should be indexed.
- Large joins may need query plan inspection.
- Aggregating after a one-to-many join can overcount.

### Scalability And Reliability

- Heavy joins on hot paths can bottleneck the primary DB.
- Read replicas can serve analytics-style joins.
- Denormalization can help read performance but complicates writes.

### Common Mistakes

- Application loops making one query per row.
- `SELECT *` across multiple joined tables.
- Ignoring nulls from outer joins.

### Quick Revision

- `INNER` requires matches.
- `LEFT` preserves left-side rows.
- Join filters belong carefully in `ON` vs `WHERE`.

---

## Transactions

### Concept

A transaction groups database operations so they commit together or roll back together.

ACID:

- Atomicity: all or nothing.
- Consistency: constraints preserved.
- Isolation: concurrent transactions do not corrupt each other.
- Durability: committed data survives failures.

### Backend Example

```python
async def reserve_order_capacity(session, account_id: str, notional: float):
    async with session.begin():
        account = await session.get(Account, account_id, with_for_update=True)
        if account.used_notional + notional > account.max_notional:
            raise RiskLimitExceeded()

        account.used_notional += notional
        session.add(OrderReservation(account_id=account_id, notional=notional))
```

### SQL Example

```sql
BEGIN;

SELECT used_notional, max_notional
FROM account_limits
WHERE account_id = 'acct_123'
FOR UPDATE;

UPDATE account_limits
SET used_notional = used_notional + 50000
WHERE account_id = 'acct_123';

INSERT INTO order_reservations(account_id, notional)
VALUES ('acct_123', 50000);

COMMIT;
```

### Isolation Levels

| Level | Prevents | Still Allows |
|---|---|---|
| Read committed | Dirty reads | Non-repeatable reads |
| Repeatable read | Non-repeatable reads | Some serialization anomalies |
| Serializable | Most anomalies | More conflicts/retries |

### Production Relevance

Transactions protect money, positions, orders, inventory, risk limits, and idempotency records.

### Interview Traps

- Doing external HTTP calls inside long DB transactions.
- Assuming transactions solve distributed consistency.
- No retry handling for serialization failures/deadlocks.
- Reading then writing without locks or constraints.

### Performance Considerations

- Keep transactions short.
- Index rows being locked.
- Avoid user/network waits inside transactions.
- High isolation can reduce concurrency.

### Scalability And Reliability

- Transactions give strong local consistency.
- Distributed workflows often need sagas/outbox patterns.
- Unique constraints plus transactions are reliable idempotency tools.

### Quick Revision

- Commit persists; rollback discards.
- Isolation controls concurrency anomalies.
- Keep transactions short and deterministic.

---

## Concurrency Problems

### Concept

Concurrency bugs happen when multiple tasks, threads, processes, or services interact with shared state at the same time.

### Common Problems

| Problem | Example |
|---|---|
| Race condition | Two orders reserve the same remaining risk limit |
| Deadlock | Two transactions lock resources in opposite order |
| Lost update | Last write overwrites earlier update |
| Shared state bug | Global dict mutated by multiple threads |
| Duplicate work | Two workers process same job |

### Python Example

```python
import threading

lock = threading.Lock()
positions: dict[str, int] = {}

def apply_fill(symbol: str, quantity: int):
    with lock:
        positions[symbol] = positions.get(symbol, 0) + quantity
```

For multi-process or multi-service systems, use database constraints, row locks, queues, or distributed coordination instead of in-memory locks.

### SQL Lost Update Fix

```sql
UPDATE account_limits
SET used_notional = used_notional + :delta
WHERE account_id = :account_id
  AND used_notional + :delta <= max_notional;
```

Check affected row count. If zero, reject.

### Interview Traps

- Saying the Python GIL prevents all races.
- Using local locks for distributed workers.
- Ignoring transaction isolation.
- No deadlock retry strategy.

### Performance Considerations

- Locks reduce concurrency.
- Fine-grained locks improve throughput but increase complexity.
- Optimistic concurrency works well when conflicts are rare.

### Scalability And Reliability

- Prefer atomic database updates for shared durable state.
- Queue partitioning can serialize per-key processing.
- Idempotent workers reduce duplicate-processing damage.

### Quick Revision

- GIL does not make application logic race-free.
- Use the right lock scope: thread, process, DB row, distributed.
- Atomic updates and constraints beat ad hoc checks.

---

## Queues And Workers

### Concept

Queues decouple producers from consumers. Workers process jobs asynchronously.

### Why It Matters

Queues smooth bursts, isolate slow work, retry failures, and let APIs return quickly.

### Producer-Consumer Example

```python
from rq import Queue
from redis import Redis

redis_conn = Redis(host="redis", port=6379)
queue = Queue("reconciliation", connection=redis_conn)

def enqueue_reconciliation(account_id: str):
    queue.enqueue("jobs.reconcile_account", account_id, retry=3, job_timeout=300)
```

Worker function:

```python
def reconcile_account(account_id: str):
    # Must be idempotent because jobs can be retried.
    last_cursor = load_checkpoint(account_id)
    events = fetch_exchange_events(account_id, cursor=last_cursor)
    apply_events_once(account_id, events)
    save_checkpoint(account_id, events[-1].cursor)
```

### Production Concepts

- Dead-letter queue for poison messages.
- Visibility timeout or lease.
- Retry count and backoff.
- Idempotent job handlers.
- Queue lag monitoring.
- Partitioning by key for ordering.

### Interview Traps

- No dead-letter queue.
- Infinite retries on poison messages.
- Assuming exactly-once processing.
- Ignoring job ordering requirements.

### Performance Considerations

- Increase workers for parallelism only if downstream can handle it.
- Batch small jobs when overhead dominates.
- Monitor queue age, not only queue length.

### Scalability And Reliability

- Queues improve resilience by absorbing bursts.
- Backpressure prevents APIs from overwhelming workers.
- Durable queues survive worker restarts.

### Quick Revision

- Queues decouple and buffer.
- Workers must be idempotent.
- Monitor lag, retries, and dead letters.

---

## Distributed Systems Basics

### Concept

A distributed system has multiple nodes communicating over unreliable networks. Failures are partial: one service can be down while others are running.

### Core Ideas

| Concept | Practical Meaning |
|---|---|
| Horizontal scaling | Add instances |
| Replication | Copy data for availability/read scale |
| Consistency | Agreement on data values |
| Fault tolerance | Continue despite failures |
| Coordination | Agree who does what |

### CAP Theorem

During a network partition, a distributed system must choose between:

- Consistency: all clients see the same latest data.
- Availability: every request receives a non-error response.

In interviews, do not overuse CAP. Explain the actual failure and user impact.

### Production Example

```text
Order API accepts request -> persists idempotency record -> publishes order command
Worker consumes command -> sends to exchange -> records exchange ack -> emits event
Read API serves order status from DB/read model
```

### Interview Traps

- Pretending networks are reliable.
- No timeout/retry/idempotency story.
- Assuming exactly-once delivery.
- Ignoring clock skew.
- No plan for partial failure.

### Performance Considerations

- Cross-service calls add latency and failure points.
- Fan-out increases tail latency.
- Replication lag affects read-after-write behavior.

### Scalability And Reliability

- Stateless services scale easily.
- Stateful systems require partitioning, replication, and failover design.
- Distributed transactions are expensive; prefer local transactions plus events when possible.

### Quick Revision

- Partial failure is normal.
- Exactly-once is rare; design idempotent processing.
- Replication improves availability but introduces lag/conflict.

---

## Idempotency

### Concept

An operation is idempotent if repeating it produces the same final effect. This is critical when clients retry after timeouts.

### Backend Example

```sql
CREATE TABLE idempotency_keys (
    key text PRIMARY KEY,
    request_hash text NOT NULL,
    status text NOT NULL,
    response_json jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);
```

```python
async def create_order_once(session, key: str, payload: dict):
    payload_hash = stable_hash(payload)
    async with session.begin():
        existing = await get_idempotency_record(session, key, for_update=True)
        if existing:
            if existing.request_hash != payload_hash:
                raise IdempotencyConflict()
            return existing.response_json

        await insert_idempotency_record(session, key, payload_hash, status="PROCESSING")
        order = await create_order(session, payload)
        response = {"order_id": order.id, "status": order.status}
        await mark_idempotency_complete(session, key, response)
        return response
```

### Production Relevance

In trading, timeout does not mean failure. The exchange may have accepted the order, while the client never received the response.

### Duplicate Request Handling

- Require `Idempotency-Key` for dangerous creates.
- Store request hash to reject key reuse with different payload.
- Return original response for duplicates.
- Expire old keys after a business-safe TTL.

### Interview Traps

- Saying "just retry" for order placement.
- Idempotency key stored only in memory.
- No atomicity between idempotency record and side effect.
- No duplicate handling in workers.

### Performance Considerations

- Idempotency table can become hot.
- Use TTL/partitioning/cleanup.
- Unique indexes protect correctness.

### Scalability And Reliability

- Idempotency enables safe retries.
- It reduces duplicate orders, duplicate payments, and duplicate jobs.
- Must be enforced in durable shared storage.

### Quick Revision

- Retry safety depends on idempotency.
- Store key, request hash, status, and response.
- Timeout is unknown outcome, not guaranteed failure.

---

## Horizontal Scaling

### Concept

Horizontal scaling means adding more service instances instead of making one machine larger.

### Requirements

- Stateless application instances.
- Shared external state: DB, Redis, queue, object store.
- Load balancing.
- Health checks.
- Config and secrets management.
- Observability per instance and aggregate.

### Stateless Handler Example

```python
@app.get("/v1/positions/{account_id}")
async def positions(account_id: str, session=Depends(get_session)):
    # No process-local session state required.
    return await load_positions(session, account_id)
```

### Bottlenecks

| Bottleneck | Symptom | Fix |
|---|---|---|
| Database | Slow queries, pool exhaustion | Indexing, read replicas, caching |
| Shared cache | Redis CPU/memory high | Key design, sharding, TTL |
| Downstream API | Timeouts, 5xx | Backpressure, queueing, circuit breaker |
| Stateful app | Sticky sessions required | Externalize session state |

### Interview Traps

- Scaling app servers while DB is bottlenecked.
- Ignoring connection pool multiplication.
- Keeping mutable in-memory state.
- No deployment/rollback strategy.

### Performance Considerations

- Horizontal scaling can increase downstream pressure.
- More replicas means more open DB connections.
- Autoscaling reacts after load, not before.

### Scalability And Reliability

- Multiple instances improve availability.
- Stateless design enables rolling deploys.
- Shared dependencies become the next reliability focus.

### Quick Revision

- Stateless app servers scale horizontally.
- State moves to durable shared systems.
- Scaling one layer often exposes the next bottleneck.

---

## Load Balancing Basics

### Concept

Load balancers distribute traffic across backend instances and remove unhealthy instances from rotation.

### Common Types

| Type | Example | Use |
|---|---|---|
| L4 | TCP load balancer | Fast transport-level routing |
| L7 | HTTP reverse proxy | Path/header routing, TLS, retries |
| Reverse proxy | Nginx, Envoy, HAProxy | Front app services |

### Algorithms

- Round robin: simple distribution.
- Least connections: useful for variable request time.
- Weighted: shift traffic by capacity/version.
- Consistent hashing: route same key to same backend.
- Sticky sessions: same client to same instance, but hurts statelessness.

### Nginx-Style Example

```nginx
upstream api_backend {
    server api-1:8000;
    server api-2:8000;
}

server {
    listen 80;
    location / {
        proxy_set_header X-Request-ID $request_id;
        proxy_pass http://api_backend;
    }
}
```

### Production Relevance

Load balancers support high availability, rolling deploys, TLS termination, routing, health checks, and backpressure.

### Interview Traps

- No health checks.
- Sticky sessions used to hide stateful app design.
- Load balancer retries unsafe requests.
- Ignoring timeout mismatch between LB and app.

### Performance Considerations

- L7 routing costs more but gives more control.
- Keepalive reduces connection setup overhead.
- Bad retry policies can duplicate writes.

### Scalability And Reliability

- Health checks prevent traffic to bad instances.
- Multi-AZ load balancing improves availability.
- Load balancer can become a critical dependency if not redundant.

### Quick Revision

- LB distributes traffic and handles health.
- Reverse proxies add HTTP-aware control.
- Sticky sessions are usually a smell for API services.

---

# Cross-Cutting Production Patterns

## Exchange Connectivity And HFT-Oriented Backend Concerns

### What Matters

Exchange-facing services are more latency- and correctness-sensitive than normal CRUD APIs. Failures can create financial exposure, duplicate orders, stale positions, or missed cancels.

### Practical Design

```text
Market data feed -> normalizer -> in-memory book/cache -> strategy/risk consumers
Order API -> risk check -> order gateway -> exchange protocol adapter -> ack/fill processor
Fills -> durable event log -> position service -> reconciliation
```

### Production Pitfalls

- Treating network timeout as rejected order.
- No sequence-number gap detection on market data.
- No heartbeat/liveness detection for exchange sessions.
- Clock drift between systems.
- Slow consumer causing message backlog.
- Logging too much on hot paths.

### Python Performance Notes

- Python is good for orchestration, APIs, control planes, automation, and moderate-throughput services.
- For ultra-low latency paths, use native components, optimized networking, colocated services, or C++/Rust/Java where required.
- In Python, reduce allocations, avoid unnecessary serialization, use async for I/O, and keep CPU-heavy paths out of the event loop.

### Quick Revision

- Correctness beats raw speed in order lifecycle systems.
- Track sequence numbers, heartbeats, and reconciliation.
- Always design for unknown order state after timeout.

---

## Linux Production Environments

### What To Know

Backend/HFT interviews often test practical Linux debugging.

Useful commands:

```bash
systemctl status trading-api
journalctl -u trading-api -n 200 --no-pager
ss -tanp | grep 8000
lsof -i :8000
top
htop
df -h
free -m
ulimit -n
```

### Production Scenarios

- Process running but not accepting connections: check bind address, port, firewall, listener, logs.
- High latency: check CPU steal, run queue, GC, DB latency, network, saturation.
- Too many open files: check `ulimit`, connection leaks, log files, sockets.
- Disk full: logs, core dumps, temp files, database volume.

### Quick Revision

- Know how to inspect processes, ports, logs, disk, memory, and file descriptors.
- Many backend incidents are resource exhaustion incidents.

---

## Infrastructure Automation

### Practical Focus

Infrastructure automation makes environments reproducible and deploys safer.

Relevant concepts:

- Docker images.
- CI/CD pipelines.
- Environment-specific config.
- Secrets management.
- Terraform/CloudFormation basics.
- Kubernetes deployments, services, config maps, secrets, probes.
- Rollbacks and blue/green or canary deploys.

### Production Pitfalls

- Manual server changes not tracked.
- Secrets in git.
- No rollback.
- Config drift across environments.
- Deploying without health checks.

### Quick Revision

- Automate repeatable infrastructure.
- Treat config and secrets carefully.
- Deployment safety is part of backend engineering.

---

# Top 30 Backend/System Interview Questions

1. How would you design an order placement API that is safe to retry?
2. What is the difference between authentication and authorization?
3. When should an API return `400`, `409`, `429`, `500`, and `503`?
4. How do you design cursor pagination for a changing dataset?
5. Why should backend services be stateless?
6. What happens if a client times out after submitting an order?
7. How do you prevent duplicate processing in a worker system?
8. How do you size a database connection pool?
9. How do indexes speed up queries, and what do they cost?
10. Why can `OFFSET` pagination be problematic at scale?
11. What is the difference between logs, metrics, and traces?
12. What alerts would you create for a trading API?
13. How do retries cause outages?
14. What is exponential backoff with jitter?
15. How would you debug a sudden spike in p99 latency?
16. How do you handle Redis being unavailable?
17. What is the difference between `PUT` and `PATCH`?
18. What does idempotency mean for `POST /orders`?
19. How do transactions prevent race conditions?
20. What isolation level would you choose and why?
21. How can deadlocks happen in a database?
22. How do queues improve reliability?
23. What is a dead-letter queue?
24. What are the tradeoffs of JWT vs sessions?
25. How does a load balancer detect unhealthy instances?
26. What breaks when you horizontally scale a stateful app?
27. How would you design rate limiting across multiple instances?
28. How do you detect stale market data or missed exchange messages?
29. What Linux commands help debug a production service?
30. How would you design a system to reconcile exchange fills with internal order state?

---

# One-Hour Before Interview Revision

Revise these first:

- Idempotency for writes, especially orders/payments.
- Timeouts, retries, backoff, retry storms.
- Status codes and error response design.
- Cursor pagination and indexing.
- Connection pooling and pool exhaustion.
- Transactions, isolation, locks, deadlocks.
- Logs vs metrics vs traces; p95/p99 latency.
- Queues, retries, DLQs, idempotent workers.
- Stateless services and horizontal scaling.
- Redis: cache, TTL, rate limit, locks, queues.
- Load balancers, health checks, readiness vs liveness.
- Exchange timeout means unknown state, not failure.
- Production debugging: logs, metrics, traces, DB, network, Linux resources.

Memorize these lines:

- "Timeout means I do not know the outcome."
- "Retries require idempotency."
- "Averages hide tail latency."
- "Scaling app replicas can overload the database."
- "A queue gives buffering, not exactly-once processing."
- "A cache improves latency but introduces staleness."

---

# Most Common Backend Engineering Mistakes

- No timeouts on network calls.
- Retrying non-idempotent operations.
- Returning `200` for errors.
- No pagination or unbounded page sizes.
- Logging secrets or full sensitive payloads.
- Using average latency instead of percentiles.
- Creating DB/HTTP clients per request.
- Oversizing connection pools.
- Missing indexes on hot query paths.
- Adding too many indexes without write-cost awareness.
- Long transactions with external calls inside.
- In-memory locks used for distributed coordination.
- Workers that are not idempotent.
- Infinite retries without DLQ.
- Cache keys missing tenant/account dimensions.
- No TTL on Redis keys.
- No readiness checks.
- No correlation IDs.
- Alerting without runbooks or user impact.
- Treating exchange/API timeouts as definitive failures.

---

# Quick HFT / Backend Production Engineering Tips

- Use sequence numbers to detect dropped or out-of-order market data.
- Track heartbeats for exchange sessions and internal streams.
- Separate hot data paths from slow admin/control APIs.
- Keep order state transitions explicit and auditable.
- Reconcile internal state with exchange state continuously.
- Prefer monotonic clocks for elapsed-time measurement.
- Monitor p99 and max latency for latency-sensitive paths.
- Avoid blocking calls in async event loops.
- Do not log per-message hot-path data unless sampled.
- Pre-allocate or reuse objects where Python allocation overhead matters.
- Use bounded queues to create backpressure.
- Make kill switches and circuit breakers operationally visible.
- Design every external call with timeout, retry policy, and idempotency decision.
- Use canaries for risky deploys.
- Keep runbooks close to alerts.

---

# Mini Backend Coding Exercises

## 1. Idempotent Order Create

Build `POST /orders` with:

- Required `Idempotency-Key`.
- Request hash comparison.
- Unique DB constraint.
- Original response replay.
- Conflict on same key with different payload.

## 2. Cursor Pagination

Implement `GET /orders?limit=100&cursor=...` using:

- Stable sort by `created_at DESC, id DESC`.
- Composite index.
- No `OFFSET`.
- Next cursor in response.

## 3. Retry Wrapper

Write an async HTTP client wrapper with:

- Connect/read/pool timeouts.
- Retry only transient `5xx`/timeouts.
- Exponential backoff with jitter.
- No retry for `400`, `401`, `403`, `409`.

## 4. Rate Limiter

Implement Redis token bucket:

- Keyed by API client.
- Atomic Lua script.
- Burst and refill rate.
- Return `429` and `Retry-After`.

## 5. Worker With DLQ

Create a worker that:

- Processes jobs idempotently.
- Retries transient failures.
- Sends poison messages to DLQ.
- Emits queue lag and retry metrics.

## 6. Slow Query Investigation

Given a slow endpoint:

- Capture query.
- Run `EXPLAIN ANALYZE`.
- Identify missing index or bad join.
- Add targeted index.
- Verify p95/p99 improvement.

---

# Real-World Production Debugging Scenarios

## Scenario 1: API p99 Latency Spikes

Check:

- Recent deploys.
- DB query latency and pool wait time.
- Redis latency.
- Downstream service latency.
- CPU, memory, GC, file descriptors.
- Load balancer target health.
- Request volume and slow endpoints.

Likely causes:

- Missing index.
- Pool exhaustion.
- Downstream timeout.
- Retry storm.
- Large response payload.

## Scenario 2: Duplicate Orders

Check:

- Client retries after timeout.
- Missing or ignored idempotency key.
- Worker processed same message twice.
- Exchange ack delayed.
- DB unique constraint missing.

Fix:

- Durable idempotency records.
- Unique constraints.
- Idempotent worker state transitions.
- Reconciliation with exchange.

## Scenario 3: Queue Lag Increasing

Check:

- Producer rate vs consumer rate.
- Worker error/retry rate.
- Downstream dependency latency.
- Poison messages.
- Worker autoscaling.
- Partition hot spots.

Fix:

- Add workers only if downstream can handle it.
- Batch jobs.
- Move poison messages to DLQ.
- Add backpressure to producers.

## Scenario 4: Redis Memory High

Check:

- Keys without TTL.
- Large values.
- Hot key patterns.
- Eviction policy.
- Recent feature storing unbounded data.

Fix:

- Add TTLs.
- Compress or split large values.
- Cap list/stream lengths.
- Monitor memory and eviction count.

## Scenario 5: Database Deadlocks

Check:

- Transaction lock order.
- Long-running transactions.
- Missing indexes causing broad locks.
- Concurrent updates to same rows.

Fix:

- Consistent lock ordering.
- Shorter transactions.
- Targeted indexes.
- Retry deadlock victims.

## Scenario 6: Exchange Disconnect

Check:

- Heartbeats.
- Network path.
- Auth/session expiry.
- Sequence gaps.
- Reconnect logic.
- Order state during disconnect.

Fix:

- Stop sending if session unhealthy.
- Reconnect with backoff.
- Resubscribe and verify sequence.
- Reconcile open orders/fills.

---

# Common Reliability / System Design Interview Scenarios

## Design A Trading Order API

Must include:

- Auth and authorization.
- Risk checks.
- Idempotency key.
- Durable order state.
- Exchange gateway.
- Timeout handling with unknown state.
- Reconciliation.
- Metrics and alerts.

## Design Internal Operations Dashboard Backend

Must include:

- Paginated APIs.
- Role-based access.
- Read replicas or cached views for heavy reads.
- Audit logs for actions.
- Structured errors.
- Correlation IDs.

## Design Exchange Connectivity Service

Must include:

- Protocol adapter.
- Session lifecycle.
- Heartbeats.
- Sequence number handling.
- Reconnect behavior.
- Order/fill state machine.
- Reconciliation job.

## Design Distributed Rate Limiter

Must include:

- Key choice: user/account/API key/IP.
- Redis or local plus global budget.
- Atomic increments/token bucket.
- `429` and `Retry-After`.
- Fail-open vs fail-closed decision.
- Metrics by client and endpoint.

## Design Reliable Worker System

Must include:

- Durable queue.
- Idempotent job processing.
- Retry with backoff.
- DLQ.
- Visibility timeout.
- Queue lag metrics.
- Backpressure.

## Design Monitoring For Backend Service

Must include:

- RED metrics.
- Dependency metrics.
- p95/p99 latency.
- Error budget/SLO.
- Health checks.
- Logs with request IDs.
- Traces for slow distributed requests.
- Alerts with runbooks.

---

# Final Mental Model

Production backend engineering is mostly about controlled failure:

- Bound every wait with a timeout.
- Make retries safe with idempotency.
- Keep services stateless when possible.
- Use durable storage for shared truth.
- Add observability before incidents.
- Protect dependencies with pools, queues, rate limits, and backpressure.
- Assume networks fail and outcomes can be unknown.
- In HFT/trading systems, correctness, auditability, and reconciliation are as important as latency.
