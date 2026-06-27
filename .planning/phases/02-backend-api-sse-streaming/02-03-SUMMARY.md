---
phase: 02-backend-api-sse-streaming
plan: 03
subsystem: api
tags: [asyncio, fastapi, sqlite, snapshots, background-tasks]

# Dependency graph
requires:
  - phase: 02-backend-api-sse-streaming
    plan: 01
    provides: REST routers, Pydantic schemas, FastAPI deps, and SNAP-02 inline snapshot call in /api/portfolio/trade
provides:
  - backend/app/snapshots.py — 30s background loop that writes portfolio_snapshots rows on a fixed cadence
  - FastAPI lifespan wiring: snapshot task starts after market_source.start, cancels before close_db
  - 8-case pytest-asyncio suite proving cadence, shutdown, error resilience, missing prices, SNAP-02, and lifespan wiring
affects: [phase-04-frontend, phase-03-portfolio-api-history]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.wait_for(stop_event.wait(), timeout=interval) for bounded shutdown without busy-waiting"
    - "Per-iteration try/except so one DB insert failure never kills the background loop"
    - "AppState dataclass fields snapshot_task + _snapshot_stop for test introspection"

key-files:
  created:
    - backend/app/snapshots.py
    - backend/tests/snapshots/__init__.py
    - backend/tests/snapshots/test_snapshot_loop.py
  modified:
    - backend/app/main.py

key-decisions:
  - "Trade-time snapshot (SNAP-02) lives in the trade handler; cadence snapshot (SNAP-01) lives in a background task — single source per write path avoids double-writes"
  - "Compute total in dollars throughout; cents conversion is centralized inside SnapshotRepository.insert"
  - "Loop uses asyncio.wait_for(stop_event.wait(), timeout=interval) so shutdown completes within at most one interval without polling"
  - "TestClient runs lifespan on its own portal event loop, so structural-only assertions on the task (presence/cleared) instead of cross-loop await"

patterns-established:
  - "Snapshot loop: while not stop_event.is_set(): try insert; except log+continue; wait_for(stop, interval)"
  - "Compute total = cash + sum(qty * cache_price or 0) — default to 0 for missing prices to never crash"
  - "Shutdown order: stop snapshot loop → stop market source → close DB (so the in-flight insert cannot race close_db)"

requirements-completed: [SNAP-01, SNAP-02]

# Coverage metadata (#1602) — per-deliverable Requirements Traceability Matrix.
coverage:
  - id: D1
    description: "Background asyncio task records portfolio_snapshots rows every 30s (SNAP-01) via app.snapshots.start_snapshot_loop wired into the FastAPI lifespan"
    requirement: SNAP-01
    verification:
      - kind: unit
        ref: tests/snapshots/test_snapshot_loop.py#test_snapshot_loop_writes_rows_on_cadence
        status: pass
      - kind: unit
        ref: tests/snapshots/test_snapshot_loop.py#test_snapshot_loop_respects_stop_event
        status: pass
      - kind: unit
        ref: tests/snapshots/test_snapshot_loop.py#test_snapshot_loop_survives_insert_failure
        status: pass
      - kind: unit
        ref: tests/snapshots/test_snapshot_loop.py#test_lifespan_starts_and_stops_snapshot_loop
        status: pass
    human_judgment: false
  - id: D2
    description: "_compute_total_value math: cash + sum(qty * live_price or 0) — missing prices contribute 0"
    requirement: SNAP-01
    verification:
      - kind: unit
        ref: tests/snapshots/test_snapshot_loop.py#test_compute_total_value_with_only_cash
        status: pass
      - kind: unit
        ref: tests/snapshots/test_snapshot_loop.py#test_compute_total_value_includes_position_value
        status: pass
      - kind: unit
        ref: tests/snapshots/test_snapshot_loop.py#test_snapshot_loop_uses_zero_for_missing_prices
        status: pass
    human_judgment: false
  - id: D3
    description: "POST /api/portfolio/trade inserts exactly one snapshot row per successful trade (SNAP-02)"
    requirement: SNAP-02
    verification:
      - kind: unit
        ref: tests/snapshots/test_snapshot_loop.py#test_trade_records_inline_snapshot
        status: pass
      - kind: integration
        ref: tests/api/test_portfolio.py#test_trade_buy_decrements_cash_and_creates_position
        status: pass
      - kind: integration
        ref: tests/api/test_portfolio.py#test_portfolio_history_returns_snapshots_ordered_asc
        status: pass
    human_judgment: false

# Metrics
duration: 12min
completed: 2026-06-27
status: complete
---

# Phase 2 Plan 3: Snapshot Loop Summary

**30s background asyncio task plus trade-time inline insert recording `cash + Σ(qty * live_price)` into `portfolio_snapshots` for the Phase 4 P&L chart**

## Performance

- **Duration:** 12 min
- **Started:** 2026-06-27T12:16:25Z
- **Completed:** 2026-06-27T12:28:07Z
- **Tasks:** 2/2 complete
- **Files modified:** 4 (1 new module + 1 test package with 8 cases + 1 modified main.py)

## Accomplishments

- `backend/app/snapshots.py` — `start_snapshot_loop(price_cache, stop_event, interval_seconds=30.0) -> asyncio.Task` plus the testable helper `_compute_total_value(price_cache)`. Loop uses `asyncio.wait_for(stop_event.wait(), timeout=interval)` for bounded shutdown and wraps each iteration in `try/except Exception` so a single failed insert never kills the loop.
- FastAPI lifespan in `backend/app/main.py` starts the snapshot task immediately after `market_source.start(tickers)` and shuts it down (`stop_event.set()` + `task.cancel()` + `await task`) before `market_source.stop()` and `close_db()`. `AppState` gained `snapshot_task` and `_snapshot_stop` fields for test introspection.
- Verified SNAP-02 was already wired inline in `POST /api/portfolio/trade` (Plan 02-01) — no duplicate snapshot insert added.
- 8-case pytest-asyncio suite at `backend/tests/snapshots/test_snapshot_loop.py` covers math (cash-only, post-buy, missing-prices), cadence (≥3 rows in 1.7s @ 0.5s interval), shutdown (DB count stops growing after stop_event), error resilience (RuntimeError on first insert; loop recovers), trade-time delta (exactly +1 row per trade), and lifespan structural invariants (task present on enter, cleared on exit).

## Task Commits

Each task was committed atomically:

1. **Task 1: Snapshot loop module + lifespan wiring** — `4dc2ca7` (feat)
2. **Task 2: Pytest-asyncio suite for loop and trade-time snapshots** — `c754b15` (test)

## Files Created/Modified

- `backend/app/snapshots.py` — New module: `start_snapshot_loop`, `_snapshot_loop`, `_compute_total_value`. Bounded shutdown via `wait_for(stop, interval)`, per-iteration try/except, dollars-throughout math.
- `backend/app/main.py` — Lifespan startup: starts `snapshot_task` after `market_source.start(tickers)`. Shutdown: sets `_snapshot_stop`, cancels + awaits task BEFORE `close_db()`. `AppState` gains `snapshot_task` and `_snapshot_stop`.
- `backend/tests/snapshots/__init__.py` — Empty package marker.
- `backend/tests/snapshots/test_snapshot_loop.py` — 8 pytest-asyncio cases (see Accomplishments).
- `backend/app/api/portfolio.py` — Verified; no change. The Plan 02-01 inline SNAP-02 call at line 206 (`await snapshot_repo.insert(new_cash_dollars + positions_value)`) was already in place; not duplicated.

## Decisions Made

- **Single writer per source.** SNAP-02 lives in the trade handler; SNAP-01 lives in the background loop. The trade-time call is not duplicated in the loop, and the loop's 30s cadence is too sparse to overlap meaningfully with the unpredictable trade path.
- **Math in dollars, conversion in one place.** `SnapshotRepository.insert` is the only place dollars→cents conversion happens for snapshots. The loop never touches cents.
- **Bounded shutdown without busy-waiting.** `asyncio.wait_for(stop_event.wait(), timeout=interval)` gives both immediate wake-up on stop AND no CPU spin during the wait. Fallback path: `task.cancel()` then `await task` guarantees teardown even if `wait_for` is mid-flight.
- **Shutdown ordering matters.** Stop the snapshot loop BEFORE closing the DB so an in-flight `await db.execute(...)` doesn't race `await _connection.close()`.
- **Cross-loop test pattern.** `TestClient` runs lifespan on its own portal loop. Asserting `task.done()` from the test's pytest-asyncio loop raises "attached to a different loop". The test suite therefore checks structural state (presence/cleared of `state.snapshot_task`, count behavior over wall-clock sleep) instead of cross-loop awaits.

## Deviations from Plan

None — plan executed exactly as written. The Plan 02-01 inline SNAP-02 call was already in `portfolio.py` (verified at line 206) so no change was needed there. `app.state.snapshot_stop = state._snapshot_stop` was added in addition to the state on `state._snapshot_stop` so the stop event is reachable via `request.app.state` for any future dependency overrides.

## Issues Encountered

- **Cross-loop `await` of the lifespan task** (initial test failure on `test_snapshot_loop_respects_stop_event`). The lifespan task is bound to TestClient's internal portal loop, not pytest-asyncio's test loop, so `await asyncio.wait_for(main.state.snapshot_task, timeout=1.0)` raised `RuntimeError: ... attached to a different loop`. Resolved by asserting only DB-row-count behavior after `stop_event.set()` instead of awaiting the task from the test loop. This is consistent with how the existing `seeded_client` fixture interacts with the lifespan-managed `market_source` task.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 2 Plan 03 (this plan) closes the snapshot story: SNAP-01 cadence + SNAP-02 inline. `portfolio_snapshots` is now a reliable time series for the P&L chart.
- Phase 4 frontend can poll `GET /api/portfolio/history` for historical snapshots to draw the P&L chart; `GET /api/portfolio` for current value.
- Phase 3 (chat + LLM) does not depend on this plan.

## Self-Check

- **PASSED**
- Files exist: `backend/app/snapshots.py`, `backend/tests/snapshots/__init__.py`, `backend/tests/snapshots/test_snapshot_loop.py`
- Commits present: `4dc2ca7` (Task 1), `c754b15` (Task 2)
- Verification commands from plan:
  - `grep -c 'start_snapshot_loop' backend/app/main.py` → `2` (≥1 ✓)
  - `grep -c 'SnapshotRepository' backend/app/api/portfolio.py` → `3` (≥1 ✓)
  - `uv run --extra dev pytest -q tests/snapshots/` → `8 passed in 4.94s` (≥8 ✓)
  - `uv run --extra dev pytest -q` → `142 passed` (zero regressions ✓)
- Task 1 smoke test (inline Python): `computed total = 10000.0; snapshots: count=4 min=1000000 max=1000000; OK snapshot loop writes rows and respects stop event`

---
*Phase: 02-backend-api-sse-streaming*
*Completed: 2026-06-27*
