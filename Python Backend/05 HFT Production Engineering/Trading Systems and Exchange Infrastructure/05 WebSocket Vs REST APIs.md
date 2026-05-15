# WebSocket Vs REST APIs

Tags: #websocket #rest #api #streaming #backend #trading-systems #interview

Interview lens: REST is usually the control plane; websockets are usually the real-time event plane. Trading systems often need both.

---

## Concept

REST is request-response over HTTP. A client sends a request and receives a response.

Websocket is a persistent full-duplex connection. After the handshake, both sides can send messages without creating a new HTTP request each time.

Trading use cases:

- REST: create order, cancel order, query open orders, fetch account snapshot, health/status, admin actions.
- Websocket: market data ticks, order updates, fills, positions, alerts, connection state events.

---

## Why It Matters In Trading Systems

Trading systems need command APIs and real-time updates.

REST is simple and auditable for commands, but polling REST for real-time state adds latency and load. Websockets provide push-based updates, but require more careful connection, backpressure, and recovery handling.

---

## Backend/System Relevance

REST strengths:

- simple request lifecycle
- easy authentication and authorization
- works well with load balancers
- easy to retry with idempotency
- easy to debug with logs/traces
- good for snapshots and commands

REST weaknesses:

- polling adds latency and waste
- repeated HTTP overhead
- less suitable for high-frequency streams
- client may miss changes between polls

Websocket strengths:

- low overhead after connection setup
- server push for real-time updates
- useful for market data/order events
- avoids polling storms

Websocket weaknesses:

- connection state is harder to scale
- reconnect/resubscribe logic is required
- backpressure must be handled
- load balancing needs sticky sessions or shared pub/sub
- message ordering and dedupe matter

---

## Practical Architecture

Common pattern:

```text
REST command path:
  client -> POST /orders -> order manager -> exchange connector

Websocket event path:
  exchange connector -> event bus -> websocket gateway -> client
```

The REST response should usually say "accepted for processing" or return current known state. It should not pretend that downstream execution has completed unless it actually has.

Example REST order response:

```json
{
  "order_id": "ord-123",
  "client_order_id": "cli-456",
  "status": "PENDING_SUBMIT"
}
```

Example websocket update:

```json
{
  "type": "order_update",
  "order_id": "ord-123",
  "sequence": 987654,
  "status": "ACKED",
  "exchange_order_id": "ex-999"
}
```

---

## Websocket Backend Example

Simple shape:

```python
import asyncio
import json
import websockets

async def subscribe_order_updates(uri: str, token: str) -> None:
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"op": "auth", "token": token}))
        await ws.send(json.dumps({"op": "subscribe", "channel": "orders"}))

        async for raw_message in ws:
            message = json.loads(raw_message)
            if message.get("type") == "heartbeat":
                await ws.send(json.dumps({"type": "pong"}))
                continue
            handle_order_update(message)
```

Production version also needs:

- reconnect with bounded backoff
- sequence number checks
- token refresh
- resubscription
- stale connection detection
- snapshot/replay after reconnect
- backpressure control
- structured logging with correlation IDs

---

## Latency Differences

REST latency includes:

- request creation
- TCP/TLS connection if not reused
- HTTP headers
- auth middleware
- routing
- response serialization

Websocket latency includes:

- persistent connection overhead
- message serialization
- event fanout
- client receive loop

Websockets often reduce repeated connection and polling overhead, but they do not guarantee low latency if:

- server event loop is blocked
- subscribers are slow
- messages are large
- fanout path is overloaded
- reconnection logic misses messages

---

## Scalability Concerns

REST scaling:

- mostly stateless
- horizontal scaling is straightforward
- request tracing is easier
- rate limits are per client/API key

Websocket scaling:

- each connection consumes memory and file descriptors
- need connection registry
- need pub/sub or event bus across instances
- slow clients can cause backpressure
- load balancer timeouts can kill idle connections
- deploys must drain connections gracefully

Production pattern:

```text
event bus topic: order-events
  -> websocket gateway instance A -> clients 1..N
  -> websocket gateway instance B -> clients N+1..M
```

Each gateway should track last sent sequence per client if clients need loss detection.

---

## Reconnection Handling

Client reconnect steps:

1. Detect disconnect or stale heartbeat.
2. Reconnect with jittered backoff.
3. Authenticate.
4. Resubscribe.
5. Send last received sequence if protocol supports replay.
6. Fetch REST snapshot if replay is unavailable.
7. Compare snapshot with local state.
8. Resume only after state is consistent.

Server responsibilities:

- close dead connections
- avoid unbounded send buffers
- support replay or sequence numbers
- expose connection metrics
- protect against reconnect storms

---

## Production Debugging Scenarios

Scenario: UI shows stale order status.

Check:

- Did REST order create succeed?
- Did event bus receive exchange report?
- Did websocket gateway receive event?
- Did client disconnect/reconnect?
- Did sequence gap occur?
- Was the message dropped due to slow-client backpressure?

Scenario: websocket service memory grows.

Likely causes:

- unbounded per-client queues
- slow clients not disconnected
- retaining connection objects after disconnect
- large message buffers
- subscription leak after reconnect

Scenario: clients reconnect at once after deploy.

Fixes:

- graceful connection draining
- jittered reconnects
- rate-limited auth
- capacity planning for reconnect storms

---

## Common Interview Questions And Traps

- When would you use REST vs websocket in a trading backend?
  - Answer: Use REST for commands, snapshots, and explicit reads; use websocket for continuous order, market data, and status streams.
- How do you handle missed websocket messages?
  - Answer: Use sequence numbers, replay where available, and REST snapshot resync after reconnect.
- How do you scale websocket gateways?
  - Answer: Make subscription state explicit, partition connections, use shared event fanout, and keep gateways mostly stateless.
- How do you prevent slow clients from hurting fast clients?
  - Answer: Use per-client bounded queues, drop/disconnect policies, backpressure, and no shared blocking send path.
- Why is polling REST bad for market data?
  - Answer: It adds latency, load, missed intermediate updates, and bursty traffic.
- How do you deploy a websocket service safely?
  - Answer: Use connection draining, message-schema compatibility, canaries, reconnect jitter, and monitoring for reconnect storms and lag.

Traps:

- Saying websocket is always faster without discussing reliability.
- Forgetting reconnection and resubscription.
- Ignoring backpressure.
- Treating REST response as execution confirmation.
- Not using sequence numbers.
- Using one event loop for CPU-heavy processing and websocket I/O.

---

## Quick Revision

- REST is best for commands and snapshots.
- Websocket is best for streams and real-time updates.
- Trading systems usually use both.
- Websockets need heartbeat, reconnect, replay/resync, sequencing, and backpressure.
- REST needs idempotency, deadlines, clear status semantics, and auditability.
