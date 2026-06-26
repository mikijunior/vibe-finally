---
phase: 01-database-foundation
plan: "03"
subsystem: infra
tags: [fastapi, lifespan, sqlite, market-data, integration]

requires:
  - MKT-06
  - MKT-07

provides:
  - FastAPI app with lifespan-managed PriceCache and MarketDataSource
  - Watchlist↔cache↔source sync integration
  - DB lifecycle (init_db/close_db) wired to lifespan
  - SSE streaming mounted and operational
  - Health endpoint and test endpoints for verification

affects:
  - phase-02-rest-api
  - phase-03-frontend

tech-stack:
  added: [httpx>=0.28.0]
  patterns:
    - FastAPI lifespan context manager for state lifecycle
    - Callable injection pattern to avoid import-time None
    - Module-level AppState singleton for test access

key-files:
  created:
    - backend/app/main.py
    - backend/tests/test_app_lifespan.py
  modified:
    - backend/pyproject.toml

key-decisions:
  - "Used `_get_cache()` callable pattern to avoid PriceCache being None at import time while still mounting the router at module level"
  - "Test endpoints gated on TESTING=1 env var — not active in production"
  - "Watchlist add/remove sync helpers live in main.py as test-only endpoints; Phase 2 REST layer will replace these"

patterns-established:
  - "FastAPI lifespan pattern: startup creates shared state, shutdown cleans it up"
  - "AppState dataclass as module-level singleton for shared mutable state"

requirements-completed: [MKT-06, MKT-07]

coverage:
  - id: D1
    description: "FastAPI app with lifespan managing PriceCache and MarketDataSource"
    requirement: MKT-06
    verification:
      - kind: unit
        ref: "tests/test_app_lifespan.py#test_lifespan_starts_market_source_for_default_tickers"
        status: pass
      - kind: unit
        ref: "tests/test_app_lifespan.py#test_lifespan_prices_flow_into_cache"
        status: pass
    human_judgment: false
  - id: D2
    description: "Watchlist add/remove syncs to PriceCache and MarketDataSource"
    requirement: MKT-07
    verification:
      - kind: unit
        ref: "tests/test_app_lifespan.py#test_watchlist_add_propagates_to_cache_and_source"
        status: pass
      - kind: unit
        ref: "tests/test_app_lifespan.py#test_watchlist_remove_propagates_from_cache_and_source"
        status: pass
    human_judgment: false
  - id: D3
    description: "Lifespan shutdown cleanly stops source and closes DB"
    requirement: MKT-06
    verification:
      - kind: unit
        ref: "tests/test_app_lifespan.py#test_lifespan_shutdown_stops_source_and_closes_db"
        status: pass
    human_judgment: false
  - id: D4
    description: "Health endpoint operational"
    verification:
      - kind: unit
        ref: "tests/test_app_lifespan.py#test_health_endpoint_returns_ok"
        status: pass
    human_judgment: false

duration: 11 min
completed: 2026-06-26
status: complete
---

# Phase 1 Plan 3: FastAPI Lifespan Integration Summary

**FastAPI lifespan managing PriceCache, MarketDataSource, and DB lifecycle with watchlist sync**

## Performance

- **Duration:** 11 min
- **Started:** 2026-06-26T14:41:51Z
- **Completed:** 2026-06-26T14:53:02Z
- **Tasks:** 1 (1 auto-fixed)
- **Files modified:** 4

## Accomplishments

- FastAPI app with lifespan context manager that manages the full lifecycle of PriceCache, MarketDataSource, and SQLite database
- Watchlist add/remove operations sync to both the PriceCache and MarketDataSource
- SSE stream router mounted and operational via callable injection pattern
- Health endpoint at `/health` returning `{"status": "ok"}`
- Test endpoints (`GET /cache/state`, `POST /watchlist/test-add/{ticker}`, `POST /watchlist/test-remove/{ticker}`) gated on `TESTING=1` for verification
- 6 passing pytest tests covering startup, price flow, watchlist sync, shutdown, and health endpoint
- All 104 backend tests pass (including existing market data tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: FastAPI lifespan integration** - `adacbbb` (feat)

**Plan metadata:** (no metadata commit in worktree mode)

## Files Created/Modified

- `backend/app/main.py` - FastAPI app with lifespan, AppState singleton, SSE mount, health and test endpoints
- `backend/tests/test_app_lifespan.py` - 6 tests verifying lifespan startup, price flow, watchlist sync, and shutdown
- `backend/pyproject.toml` - Added `httpx>=0.28.0` to dev dependencies

## Decisions Made

- Used `_get_cache()` callable pattern to avoid PriceCache being None at import time while still mounting the SSE router at module level
- Test endpoints are gated on `TESTING=1` environment variable and will be replaced by proper REST endpoints in Phase 2
- `AppState` dataclass serves as module-level singleton accessible by tests for state inspection

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created WatchlistRepository and repositories package**
- **Found during:** Task 1 (FastAPI lifespan integration)
- **Issue:** Plan 01-02 was supposed to create `WatchlistRepository` and `backend/app/db/repositories/` but the repository files were not committed. Imports in `main.py` would have failed.
- **Fix:** Created `backend/app/db/repositories/__init__.py` and `backend/app/db/repositories/watchlist.py` with the `WatchlistRepository` class following the plan's interface
- **Files modified:** `backend/app/db/repositories/__init__.py`, `backend/app/db/repositories/watchlist.py`
- **Verification:** All imports resolve, `WatchlistRepository().get_all()` returns seeded tickers
- **Committed in:** `adacbbb` (part of task commit)

**2. [Rule 3 - Blocking] Added httpx to dev dependencies**
- **Found during:** Task 1 (running tests)
- **Issue:** `starlette.testclient.TestClient` requires `httpx>=0.28.0` which was missing from dev dependencies
- **Fix:** Added `httpx>=0.28.0` to the dev optional-dependencies in `pyproject.toml`
- **Files modified:** `backend/pyproject.toml`, `backend/uv.lock`
- **Verification:** `uv sync --extra dev` succeeds, tests run and pass
- **Committed in:** `adacbbb` (part of task commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3 blocking issues)
**Impact on plan:** Both auto-fixes were necessary to complete the plan. WatchlistRepository was a missing prerequisite; httpx was a missing test dependency. No scope creep.

## Issues Encountered

- **TestClient context exit issue:** Initial shutdown test tried to call `client.__exit__()` after the fixture had already exited, making it a no-op. Fixed by restructuring the test to create its own `TestClient` context inside the test body.
- **Python import binding:** Swapping `db_module.close_db` didn't affect the binding inside `app.main` due to Python's import semantics. Fixed by directly checking `connection._connection` and `main.state` after context exit.

## Next Phase Readiness

- FastAPI app is runnable via `uvicorn app.main:app` with clean startup/shutdown
- PriceCache and MarketDataSource are properly integrated and tested
- Phase 2 REST endpoints (portfolio, watchlist CRUD, chat) can build on this foundation
- Database schema and seed data are in place from plans 01-01 and 01-02

---
*Phase: 01-database-foundation*
*Completed: 2026-06-26*
