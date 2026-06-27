---
phase: 02-backend-api-sse-streaming
plan: 02
subsystem: api
tags: [sse, fastapi, streaming, pytest-asyncio, httpx, uvicorn]

# Dependency graph
requires:
  - phase: 01-database-foundation
    provides: PriceCache (thread-safe, version-throttled), MarketDataSource
      simulator, FastAPI lifespan that wires cache + simulator at startup
provides:
  - Hardened SSE endpoint at /api/stream/prices with full SSE-01..SSE-05
    compliance (correct headers, retry + :connected on connect, version-
    throttled data events, 30s :keepalive comment, clean disconnect)
  - Pytest-asyncio test suite (7 tests) for the SSE behavior, integrated
    into the backend test suite (134 total tests green)
affects:
  - phase 04-frontend (EventSource('/api/stream/prices') consumer)
  - any future SSE / WebSocket-style endpoint

# Tech tracking
tech-stack:
  added:
    - httpx (already a dev dep; now used as async SSE client in tests)
    - uvicorn (programmatic server fixture in tests)
  patterns:
    - Async generators wrapped in StreamingResponse for SSE
    - Fresh APIRouter per factory call so tests can inject isolated
      PriceCache instances without colliding with the module-level singleton
    - Helper `_resolve_cache()` accepting either PriceCache or zero-arg
      callable (matches the late-resolving DI pattern used in main.py)
    - Programmatic uvicorn + httpx async client for testing long-lived
      SSE responses (TestClient.stream blocks indefinitely on live SSE)

key-files:
  created:
    - backend/tests/market/test_stream.py
  modified:
    - backend/app/market/stream.py

key-decisions:
  - "Keep `create_stream_router(price_cache: PriceCache | callable)` signature
    backward-compatible: accept either an instance (for direct tests / docs)
    or a zero-arg callable (matches how main.py wires it via `_get_cache`)."
  - "Each `create_stream_router()` call returns a fresh APIRouter rather
    than re-decorating the module-level singleton, so tests with isolated
    caches don't get the lifespan-installed simulator's data."
  - "Use 30s keepalive cadence (`: keepalive` comment) rather than data
    padding — zero payload, no proxy buffering, no bandwidth cost."
  - "Add defensive `Content-Encoding: identity` header because some
    proxies default to gzip and break SSE framing."

patterns-established:
  - "SSE handlers yield `retry: 1000\\n\\n` first so EventSource
    auto-reconnects after 1s on dropped connections"
  - "SSE handlers check `request.is_disconnected()` at the top of each
    loop iteration and `await asyncio.sleep(interval)` at the bottom —
    never busy-wait, never block on slow clients beyond the cadence"
  - "Long-lived SSE endpoints are tested with programmatic uvicorn +
    httpx.AsyncClient, not TestClient.stream (which hangs indefinitely)"

requirements-completed: [SSE-01, SSE-02, SSE-03, SSE-04, SSE-05]

coverage:
  - id: D1
    description: "SSE endpoint serves text/event-stream with required headers"
    requirement: SSE-01
    verification:
      - kind: unit
        ref: tests/market/test_stream.py#test_stream_endpoint_returns_correct_headers_and_first_events
        status: pass
    human_judgment: false
  - id: D2
    description: "SSE first two lines are retry:1000 + :connected; payload
      contains ticker/price/previous_price/timestamp/direction"
    requirement: SSE-02
    verification:
      - kind: unit
        ref: tests/market/test_stream.py#test_stream_endpoint_returns_correct_headers_and_first_events
        status: pass
    human_judgment: false
  - id: D3
    description: "SSE data events include direction field; one cache
      update produces exactly one data event (version-throttled)"
    requirement: SSE-03
    verification:
      - kind: unit
        ref: tests/market/test_stream.py#test_stream_payload_includes_direction_field
        status: pass
      - kind: unit
        ref: tests/market/test_stream.py#test_stream_version_throttling_one_event_per_bump
        status: pass
    human_judgment: false
  - id: D4
    description: "SSE emits :keepalive every 30s when cache dormant;
      no data events from an empty cache"
    requirement: SSE-04
    verification:
      - kind: unit
        ref: tests/market/test_stream.py#test_stream_emits_keepalive_when_cache_dormant
        status: pass
      - kind: unit
        ref: tests/market/test_stream.py#test_stream_no_data_event_when_cache_empty
        status: pass
    human_judgment: false
  - id: D5
    description: "SSE generator exits on client disconnect; CancelledError
      is caught and logged, never propagates"
    requirement: SSE-05
    verification:
      - kind: unit
        ref: tests/market/test_stream.py#test_stream_exits_on_disconnect
        status: pass
      - kind: unit
        ref: tests/market/test_stream.py#test_stream_handles_cancelled_error_silently
        status: pass
    human_judgment: false

# Metrics
duration: 41min
completed: 2026-06-27
status: complete
---

# Phase 02 Plan 02: SSE Streaming Endpoint Hardening Summary

**SSE endpoint at `/api/stream/prices` with 30s keepalive, version-throttled
pushes, defensive gzip headers, and a 7-case pytest-asyncio test suite proving
SSE-01 through SSE-05**

## Performance

- **Duration:** 41 min
- **Started:** 2026-06-27T11:19:32Z
- **Completed:** 2026-06-27T12:00:00Z (approx)
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `/api/stream/prices` returns 200 + `Content-Type: text/event-stream` with
  the full header set: `Cache-Control: no-cache`, `Connection: keep-alive`,
  `X-Accel-Buffering: no`, and defensive `Content-Encoding: identity`
- First two emitted lines are `retry: 1000` (browser auto-reconnect) and
  `: connected` (immediate client feedback)
- Data events are version-throttled: one `data: {...}` per `PriceCache`
  version bump — no thrash when prices are stable
- `: keepalive` SSE comment fires every 30s when prices are dormant,
  keeping the connection alive through nginx / Cloudflare / App Runner
- Generator exits cleanly on `await request.is_disconnected() == True`;
  `asyncio.CancelledError` is caught and logged so uvicorn disconnects
  never raise
- Added 7 pytest-asyncio tests covering all five SSE requirements; full
  backend suite passes (134 tests, 0 failures)

## Task Commits

Each task was committed atomically:

1. **Task 1: Harden stream.py — keepalive comment, version-throttled pushes,
   SSE headers** - `aaa6428` (feat)
2. **Task 2: Write pytest-asyncio tests for SSE behavior** - `eebd74f` (feat)

## Files Created/Modified

- `backend/app/market/stream.py` - SSE generator hardened with 30s keepalive,
  fresh-router-per-call, `_resolve_cache()` accepting instance-or-callable
- `backend/tests/market/test_stream.py` - 7 SSE pytest-asyncio tests using
  programmatic uvicorn + httpx.AsyncClient for live cases, direct generator
  driving for unit cases

## Decisions Made

- **Backward-compatible factory signature.** The plan said "do not change
  the public symbol `create_stream_router`". The existing wiring in
  `app/main.py` passes `_get_cache` (a callable) — not a PriceCache
  instance. Added `_resolve_cache()` helper that accepts either form.
  Without this, every SSE request would have hit `AttributeError: 'function'
  object has no attribute 'version'` at runtime.
- **Fresh `APIRouter` per factory call.** `@router.get("/prices")` on a
  module-level singleton registers a route only on the first call; subsequent
  calls would return a router pointing at stale closures. Creating a fresh
  router per call lets tests inject isolated PriceCache instances without
  colliding with the lifespan-installed simulator. `main.py` uses the returned
  router, so no `main.py` change required.
- **`time.monotonic()` (not `time.time()`) for the keepalive timer.**
  Wall-clock changes (NTP sync, DST) shouldn't reset the keepalive cadence.
- **30s keepalive cadence** matches typical reverse-proxy idle timeouts
  (nginx default 60s, Cloudflare 100s, App Runner 60s). A 30s keepalive
  fires twice before any default timeout, with margin.
- **Programmatic uvicorn + httpx.AsyncClient** for integration tests.
  `fastapi.testclient.TestClient.stream` blocks indefinitely on a live SSE
  response; spinning up uvicorn on a free port and using `httpx.AsyncClient`
  with a hard deadline is the only reliable pattern.
- **`.strip("\n")` on raw yielded strings in unit tests.** The generator
  yields `"retry: 1000\n\n"`; `httpx.aiter_lines` preserves the newlines.
  Test assertions strip them so the protocol-level assertions match what
  the client actually sees after SSE framing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `create_stream_router` was passed a callable, not a PriceCache**

- **Found during:** Task 1 verification
- **Issue:** `main.py` line 101 wires `create_stream_router(_get_cache)`,
  passing the function itself. The original `stream.py` immediately
  accessed `price_cache.version` which raised
  `AttributeError: 'function' object has no attribute 'version'`.
  This was a pre-existing latent bug — the SSE endpoint had never
  successfully handled a real request at runtime.
- **Fix:** Added `_resolve_cache()` helper that accepts either a
  `PriceCache` instance or a zero-arg callable returning one. No main.py
  change required.
- **Files modified:** `backend/app/market/stream.py`
- **Verification:** Task 1 verification with uvicorn + httpx returned
  `status: 200`, `content-type: text/event-stream`, `cache-control: no-cache`,
  `x-accel-buffering: no`, `content-encoding: identity`, `connection: keep-alive`,
  plus the expected `retry: 1000` / `: connected` / `data: {...}` event sequence.
- **Committed in:** `aaa6428` (Task 1 commit)

**2. [Rule 3 - Blocking] Module-level `router` singleton captured only the first closure**

- **Found during:** Task 2 (empty cache test got lifespan simulator data)
- **Issue:** `@router.get("/prices")` decorator on the module-level
  singleton registers the route only on the FIRST call to
  `create_stream_router`. Subsequent calls returned a router whose
  registered handler was still the original closure pointing at the
  lifespan-installed simulator's `PriceCache`. Tests that built a fresh
  `FastAPI()` + injected an empty `PriceCache` actually received prices
  from the lifespan's simulator because the registered route was stale.
- **Fix:** `create_stream_router()` now creates a fresh `APIRouter`
  per call. `main.py` uses the returned router, so the wiring is
  unchanged.
- **Files modified:** `backend/app/market/stream.py`
- **Verification:** `test_stream_no_data_event_when_cache_empty` passes
  with an empty cache, and `test_stream_version_throttling_one_event_per_bump`
  shows exactly one data event per single `cache.update()`.
- **Committed in:** `eebd74f` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (both blocking, both related to the
same root cause: the original factory pattern didn't match how `main.py`
wired it).

**Impact on plan:** Both auto-fixes were strictly necessary for the
endpoint to function at runtime. No scope creep.

## Issues Encountered

- **`fastapi.testclient.TestClient.stream` hangs indefinitely on live SSE.**
  Tried `ThreadPoolExecutor` + response.close() — doesn't unblock the
  reader thread because httpx holds the connection open. Switched to
  programmatic uvicorn + httpx.AsyncClient with a hard wall-clock deadline
  for integration tests. This is now a documented pattern in the test
  file header so future SSE tests follow it.
- **uvicorn `lifespan="off"` for test fixtures.** The test FastAPI apps
  don't have lifespan-managed singletons, so passing `lifespan="off"`
  avoids a noisy warning during teardown.

## Next Phase Readiness

- Phase 4 (frontend) can subscribe to `EventSource('/api/stream/prices')`
  and immediately get `retry: 1000` (auto-reconnect), `: connected` (ready
  signal), and live `data: {...}` events with full ticker/price/direction.
- Price flash animations, sparkline accumulation, and live P&L updates
  in the portfolio panel are all supported by this endpoint as-is.
- Watchlist add/remove (Phase 3) will need to coordinate with the
  SSE consumer: removing a ticker from the watchlist removes it from
  the cache (already wired in `main.py`), so subsequent `data:` events
  simply won't include it.
