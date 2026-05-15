# APIs, HTTP, And Web Frameworks

Tags: #backend #api #http #fastapi #flask #interview #production

Interview lens: describe the contract, the failure mode, and how the API behaves under retries, deploys, bad clients, and partial outages.

---

## REST APIs

### Concept

REST exposes business resources through predictable URLs and HTTP semantics.

Good resource shapes:

- `/v1/orders/{order_id}`
- `/v1/accounts/{account_id}/positions`
- `/v1/exchange-connections/{venue}/status`

Poor shapes:

- `/doTrade`
- `/getStuff`
- `/api/process`

### Why It Matters In Backend Systems

REST is the contract between services, dashboards, jobs, gateways, and operators. In trading/internal platforms, APIs often become the control plane for order management, reconciliation, risk checks, and monitoring.

### Production Relevance

- Stateless handlers allow horizontal scaling behind load balancers.
- Resource names make logs, traces, permissions, and documentation easier.
- Explicit pagination prevents large responses from hurting latency.
- Versioning prevents deployed clients from breaking during backend changes.
- Idempotency makes retrying write operations safe.

### Backend Example

```python
from fastapi import FastAPI, Header, HTTPException, Query, status
from pydantic import BaseModel

app = FastAPI()

class OrderOut(BaseModel):
    id: str
    symbol: str
    side: str
    quantity: int
    status: str

@app.get("/v1/accounts/{account_id}/orders", response_model=list[OrderOut])
async def list_orders(
    account_id: str,
    limit: int = Query(default=100, le=500),
    cursor: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    x_request_id: str | None = Header(default=None),
):
    if not account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing account_id")
    return await order_store.list_orders(
        account_id=account_id,
        limit=limit,
        cursor=cursor,
        status=status_filter,
        request_id=x_request_id,
    )
```

Example output for `GET /v1/accounts/acct-123/orders?status=OPEN&limit=2`:

```json
[
  {"id": "ord-1", "symbol": "AAPL", "side": "BUY", "quantity": 10, "status": "OPEN"},
  {"id": "ord-2", "symbol": "MSFT", "side": "SELL", "quantity": 5, "status": "OPEN"}
]
```

The URL names the resource being read: orders that belong to one account. The query parameters keep filtering and pagination explicit, and the `x-request-id` lets logs and traces connect this API call to downstream work.

### Keep In Mind

REST is not just "URLs plus JSON"; it is a contract around resources, methods, status codes, pagination, retries, and versioning. Avoid storing request/user state in process memory because a stateless API is much easier to scale and deploy safely.

### Performance Considerations

- Prefer cursor pagination for large, changing tables.
- Avoid N+1 database calls inside list endpoints.
- Set response size limits.
- Validate input at the edge before expensive downstream work.
- Use compression carefully; it saves bandwidth but costs CPU.

### Scalability And Reliability

- Stateless APIs can be scaled horizontally.
- Idempotent write APIs tolerate client retries and network timeouts.
- Clear errors reduce unsafe retry behavior.
- Health checks and dependency checks make load balancer decisions safer.

### Common Mistakes

- Returning `200 OK` for failed business operations.
- Exposing internal database IDs or implementation details unnecessarily.
- Mixing command-style endpoints with resource-style APIs without consistency.
- Adding response fields with unstable meanings.

### Quick Revision

- REST is a production contract, not just an HTTP style.
- Model resources, use standard methods, paginate lists, and version breaking changes.
- Design writes for retries, especially order placement/cancel flows.

---

## HTTP Methods

### Concept

HTTP methods communicate operation semantics.

| Method | Safe | Idempotent | Common backend use |
|---|---:|---:|---|
| `GET` | Yes | Yes | Read resource/list |
| `POST` | No | No by default | Create command/action |
| `PUT` | No | Yes | Replace full resource |
| `PATCH` | No | Usually no | Partial update |
| `DELETE` | No | Yes if repeated delete has same result | Remove/cancel resource |

Safe means the request should not intentionally mutate server state. Idempotent means repeating the same request has the same final effect.

### Why It Matters In Backend Systems

Gateways, clients, load balancers, caches, retry libraries, and monitoring tools rely on method semantics. Misusing methods creates hidden operational risk.

### Production Relevance

- `GET` can be cached and retried more safely.
- `POST` writes need explicit idempotency keys if clients may retry.
- `PUT` works well for full replacement because the desired state is explicit.
- `PATCH` needs careful validation to avoid accidental partial corruption.
- `DELETE` should define behavior when the resource is already gone.

### Backend Examples

```python
@app.post("/v1/orders", status_code=201)
async def create_order(order: OrderCreate, idempotency_key: str = Header(alias="Idempotency-Key")):
    return await order_service.create_once(order, idempotency_key=idempotency_key)

@app.put("/v1/risk-limits/{account_id}")
async def replace_risk_limits(account_id: str, body: RiskLimitConfig):
    return await risk_service.replace_limits(account_id, body)

@app.patch("/v1/orders/{order_id}")
async def amend_order(order_id: str, patch: OrderPatch):
    return await order_service.apply_amendment(order_id, patch)

@app.delete("/v1/orders/{order_id}", status_code=202)
async def cancel_order(order_id: str):
    return await order_service.request_cancel(order_id)
```

Example outcomes:

```text
POST /v1/orders                  -> 201 Created with the new order
PUT /v1/risk-limits/acct-123     -> 200 OK with the replaced config
PATCH /v1/orders/ord-1           -> 200 OK with the amended order
DELETE /v1/orders/ord-1          -> 202 Accepted because cancel may finish later
```

The method tells clients and infrastructure how safe the operation is to retry or cache. The `Idempotency-Key` on `POST` is important because creating an order has side effects, and a client may retry after a timeout.

### Keep In Mind

`POST` can be made idempotent when the server stores the key and original result. `DELETE` does not always mean immediate physical deletion; it may mean cancel requested, soft delete, or tombstone depending on the domain.

### Performance Considerations

- `GET` endpoints often carry most traffic; optimize query plans and cacheability.
- `POST` endpoints often hit consistency-critical paths; keep transactions short.
- Avoid expensive synchronous side effects inside request handlers when a durable queue is acceptable.

### Scalability And Reliability

- Correct methods help proxies and clients apply safe retry policies.
- Idempotent writes protect against duplicate orders, duplicate jobs, and duplicate payments.
- Async `202 Accepted` flows scale better for long-running operations.

### Common Mistakes

- Using `GET` for state changes because it is easy to call from a browser.
- Returning `204` with a response body.
- Treating all deletes as hard deletes.

### Quick Revision

- `GET` reads, `POST` creates/commands, `PUT` replaces, `PATCH` partially updates, `DELETE` removes/cancels.
- Idempotency is about final effect, not response identity.

---

## Status Codes

### Concept

Status codes are machine-readable API outcomes.

| Class | Meaning | Backend examples |
|---|---|---|
| `2xx` | Success | `200` read/update, `201` created, `202` accepted, `204` no body |
| `3xx` | Redirect/cache flow | `304` not modified |
| `4xx` | Client/request problem | `400`, `401`, `403`, `404`, `409`, `422`, `429` |
| `5xx` | Server/dependency problem | `500`, `502`, `503`, `504` |

### Why It Matters In Backend Systems

Clients and retry systems use status codes to decide whether to fix input, authenticate, back off, retry, or fail fast.

### Production Relevance

- `409 Conflict` is useful for idempotency conflicts or version mismatches.
- `429 Too Many Requests` protects services from abuse and overload.
- `503 Service Unavailable` tells callers a dependency or service is temporarily unhealthy.
- `504 Gateway Timeout` often points to deadline/dependency problems.

### Error Response Example

```json
{
  "error": {
    "code": "ORDER_ALREADY_FILLED",
    "message": "Order cannot be cancelled after fill",
    "request_id": "req-9f4c",
    "retryable": false
  }
}
```

This body is useful because the HTTP status explains the class of failure, while the stable `code` explains the business reason. `request_id` lets support find the exact server-side logs, and `retryable` helps clients avoid unsafe retries.

### Keep In Mind

Use `4xx` when the caller must change something and `5xx` when the server or dependency failed. Do not hide failed operations behind `200 {"success": false}` unless you have a very clear domain-level reason.

### Performance Considerations

- High `4xx` rates can mean client bugs or abuse.
- High `5xx` rates can mean deploy, capacity, dependency, or data issues.
- `429` should include backoff guidance when possible.

### Scalability And Reliability

- Correct status codes make autoscaling, alerting, client behavior, and dashboards more accurate.
- `503` plus `Retry-After` is better than slow timeouts during planned maintenance or overload.

### Common Mistakes

- Hiding all failures behind `200 {"success": false}`.
- Leaking stack traces in error bodies.
- Changing error shapes between endpoints.

### Quick Revision

- `4xx` means caller/request issue. `5xx` means server/dependency issue.
- Use `409` for conflicts, `429` for rate limits, and `503/504` for availability/deadline problems.

---

## FastAPI / Flask Basics

### Concept

FastAPI and Flask are Python web frameworks for building HTTP services.

| Area | FastAPI | Flask |
|---|---|---|
| Validation | Built in with Pydantic | Usually manual or extension-based |
| Async | First-class ASGI | Historically WSGI; async support exists but extension compatibility varies |
| Dependency injection | Built in | Usually manual |
| OpenAPI docs | Built in | Extension-based |
| Style | Typed, declarative | Minimal, flexible |

### Why It Matters In Backend Systems

Framework choice affects request validation, concurrency model, deployment, observability hooks, and how services are structured.

### Production Relevance

- FastAPI is strong for typed APIs, validation, generated docs, and async IO.
- Flask is strong for small/simple services and teams that prefer explicit control.
- Both need production servers, timeouts, health checks, config management, and metrics.

### Routing, Validation, And Dependencies

```python
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()

class OrderCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    quantity: int = Field(gt=0, le=1_000_000)
    side: str

async def current_user(authorization: Annotated[str, Header()]) -> str:
    user = await auth_service.verify_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="invalid token")
    return user.id

@app.post("/v1/orders")
async def create_order(order: OrderCreate, user_id: str = Depends(current_user)):
    return await order_service.create_order(user_id=user_id, order=order)
```

Example behavior:

```text
Missing Authorization header -> 422 validation error before the handler runs
Invalid token                 -> 401 from current_user()
quantity=0                   -> 422 because Field(gt=0) fails
Valid request                 -> create_order() receives a typed OrderCreate object
```

FastAPI validates the input before business logic runs, then dependency injection supplies the authenticated user. This keeps the route focused on the action instead of repeating parsing and auth checks in every handler.

### Middleware Example

```python
import time
from fastapi import Request

@app.middleware("http")
async def request_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = (time.perf_counter() - start) * 1000
    metrics.histogram("http_request_ms", latency_ms, tags={"path": request.url.path})
    return response
```

For each request, this middleware emits one latency sample such as `http_request_ms{path="/v1/orders"} 18.4`. That output feeds dashboards and alerts without adding metrics code to every route.

### Keep In Mind

Async frameworks help most when the slow work is IO and the libraries are async too. CPU-heavy work, blocking clients, and development servers still need proper production handling.

### Performance Considerations

- Use async drivers for high-concurrency IO paths.
- Keep CPU-heavy work off the event loop.
- Tune workers based on CPU, IO wait, and latency targets.
- Avoid large Pydantic models in extremely hot paths unless validation is needed.

### Scalability And Reliability

- Use Gunicorn/Uvicorn workers for process-level isolation.
- Add readiness and liveness endpoints.
- Use middleware for correlation IDs, metrics, auth, and request logging.
- Gracefully drain on deploy so in-flight requests finish.

### Common Mistakes

- Global mutable state for per-user/per-request data.
- No request timeout at proxy/app/downstream layers.
- No structured exception handler.

### Quick Revision

- FastAPI gives typed validation and async support; Flask gives minimal flexibility.
- Framework basics are not enough: production deployment and observability matter.

---

## API Design

### Concept

Clean API design means consistent naming, predictable behavior, stable contracts, and explicit error/retry semantics.

### Why It Matters In Backend Systems

Backend APIs live longer than the first implementation. Poor contracts create client workarounds, unsafe retries, migration pain, and operational ambiguity.

### Production Relevance

- Consistency reduces client bugs.
- Backward compatibility supports rolling deploys and old clients.
- Error bodies drive automated recovery.
- Pagination and filtering keep endpoints affordable.

### Practical Rules

| Area | Good default |
|---|---|
| Naming | Plural resources: `/orders`, `/accounts/{id}/positions` |
| Versioning | URL major versions: `/v1/...` |
| Pagination | Cursor-based for changing datasets |
| Sorting | Whitelist fields |
| Filtering | Explicit query params |
| Errors | Stable `code`, `message`, `request_id`, `retryable` |
| Compatibility | Add fields, do not rename/remove without versioning |

### Backend Example

```sql
SELECT id, created_at, symbol, status
FROM orders
WHERE account_id = :account_id
  AND (:status IS NULL OR status = :status)
  AND (:cursor_created_at IS NULL OR created_at < :cursor_created_at)
ORDER BY created_at DESC, id DESC
LIMIT :limit;
```

Example output:

```text
id     created_at           symbol  status
ord-9  2026-05-15 10:01:00  AAPL    OPEN
ord-8  2026-05-15 09:59:00  MSFT    OPEN
```

The query matches the API contract: it filters by account and optional status, returns a bounded page, and orders newest first. Cursor-style pagination avoids scanning and skipping huge offsets on large order tables.

### Keep In Mind

Design the error path and migration path as carefully as the happy path. For write APIs, always explain what happens if the client times out and retries.

### Performance Considerations

- Whitelist filters that are indexed or cheap.
- Avoid arbitrary sorting on large tables.
- Prefer cursor pagination over large `OFFSET`.
- Budget request size and response size.

### Scalability And Reliability

- Good API contracts allow clients to degrade safely.
- Compatibility makes rolling deploys and canary releases safer.
- Clear retry semantics prevent duplicate work.

### Common Mistakes

- `limit=100000` with no maximum.
- Exposing internal enum values that may change.
- Inconsistent timestamps/time zones.

### Quick Revision

- Design APIs for clients, operators, and future deployments.
- Every write API needs a retry story.

---

## Middleware Concept

### Concept

Middleware wraps the request lifecycle before and/or after the route handler.

```text
client -> middleware chain -> route handler -> middleware chain -> response
```

### Why It Matters In Backend Systems

Middleware centralizes cross-cutting concerns: auth, logging, metrics, correlation IDs, CORS, rate limits, and error handling.

### Production Relevance

- Ensures every request has consistent observability.
- Avoids duplicated auth/rate-limit code in handlers.
- Creates one place to enforce deadlines and request IDs.

### Logging Middleware Example

```python
import logging
import time
from uuid import uuid4

from fastapi import Request

logger = logging.getLogger("api")

@app.middleware("http")
async def access_log(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid4()))
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "http_request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": elapsed_ms,
        },
    )
    response.headers["x-request-id"] = request_id
    return response
```

Example log line:

```json
{"event":"http_request","request_id":"req-123","method":"POST","path":"/v1/orders","status_code":201,"latency_ms":12.7}
```

The middleware guarantees every route gets the same correlation ID and latency logging. Returning the ID in the response also lets the caller share it when reporting a problem.

### Keep In Mind

Middleware runs for every request, so keep it small and predictable. Never log secrets or swallow exceptions in a way that makes a failed request look successful.

### Performance Considerations

- Middleware runs on every request, including hot paths.
- Keep it minimal and non-blocking.
- Sample high-volume logs when needed.

### Scalability And Reliability

- Good middleware improves debugging during incidents.
- Bad middleware can take down every endpoint.
- Centralized rate limits and auth reduce inconsistent enforcement.

### Common Mistakes

- Adding DB calls in access logging middleware.
- Forgetting to propagate `x-request-id`.
- Logging request bodies with PII/secrets.

### Quick Revision

- Middleware is the right place for cross-cutting behavior.
- Keep it fast, ordered, observable, and safe.

---

## Authentication Basics

### Concept

Authentication proves who the caller is. Authorization decides what the caller can do.

| Mechanism | Best use | Main risk |
|---|---|---|
| Sessions | Browser/internal apps | Sticky state or central session dependency |
| JWT | Stateless service auth | Revocation and key rotation complexity |
| API keys | Service/client integration | Leakage and weak scoping |
| OAuth | Delegated access | Flow complexity and token handling |

### Why It Matters In Backend Systems

Trading and operations systems expose sensitive actions: order entry, cancels, risk changes, reconciliations, and admin operations. Auth bugs become financial and operational incidents.

### Production Relevance

- Tokens need expiration and rotation.
- Secrets must not appear in logs.
- Permissions should be checked at the resource level.
- Internal APIs still need identity and authorization.

### JWT Verification Sketch

```python
from fastapi import Depends, Header, HTTPException

async def require_trader(authorization: str = Header()) -> User:
    token = authorization.removeprefix("Bearer ").strip()
    claims = jwt_service.verify(token, audience="trading-api")
    if "trade:write" not in claims.get("permissions", []):
        raise HTTPException(status_code=403, detail="missing trade permission")
    return User(id=claims["sub"], permissions=claims["permissions"])

@app.post("/v1/orders")
async def create_order(order: OrderCreate, user: User = Depends(require_trader)):
    return await order_service.create_order(user.id, order)
```

Example outcomes:

```text
Valid token with trade:write       -> request reaches create_order()
Valid token without trade:write    -> 403 missing trade permission
Expired or wrong-audience token    -> verification fails before business logic
```

The code separates identity from permission. The token proves who the caller is, and the `trade:write` permission proves that caller may create orders.

### Keep In Mind

Authentication answers "who is calling"; authorization answers "what are they allowed to do". Do not trust user IDs supplied in request bodies for sensitive actions.

### Performance Considerations

- JWT validation avoids central session lookup but adds crypto work.
- Permission lookups can be cached, but revocation becomes harder.
- Auth middleware must be efficient because it runs on every protected request.

### Scalability And Reliability

- Stateless token validation scales well but complicates emergency revoke.
- Central sessions are easier to revoke but add a critical dependency.
- Authorization checks should fail closed during uncertainty.

### Common Mistakes

- Logging `Authorization` headers.
- Accepting unsigned or wrong-audience tokens.
- Missing clock-skew handling for token expiry.

### Quick Revision

- AuthN answers "who are you"; AuthZ answers "can you do this".
- Production auth needs expiry, rotation, scopes, audit logs, and secret hygiene.
