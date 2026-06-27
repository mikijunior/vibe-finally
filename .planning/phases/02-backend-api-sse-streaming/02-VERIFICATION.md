---
phase: 02-backend-api-sse-streaming
verified: 2026-06-27T14:40:00Z
status: passed
score: 15/15 must-haves verified
behavior_unverified: 0
overrides_applied: 0
overrides: []
gaps: []
deferred: []
behavior_unverified_items: []
human_verification: []
---

# Phase 2: Backend API + SSE Streaming Verification Report

**Phase Goal:** Complete REST API layer and SSE streaming for real-time price updates
**Verified:** 2026-06-27T14:40:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP Success Criteria + REQUIREMENTS)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /api/portfolio returns cash, positions with P&L, total value | VERIFIED | `backend/app/api/portfolio.py:51-101` — `get_portfolio` returns `PortfolioResponse(cash_balance, positions, total_value)` with `current_price`, `unrealized_pnl`, `pnl_percent` derived from PriceCache. 2 dedicated tests in `tests/api/test_portfolio.py`. |
| 2 | POST /api/portfolio/trade validates + executes buy/sell | VERIFIED | `backend/app/api/portfolio.py:109-215` — validates `current_price` exists, then `cost_cents <= cash_balance_cents` (buy) or `existing.quantity >= quantity` (sell) before any DB write. Rejects bad input with 400/422. 14 dedicated tests. |
| 3 | GET /api/portfolio/history returns snapshots | VERIFIED | `backend/app/api/portfolio.py:223-237` — `get_portfolio_history` returns `PortfolioHistoryResponse(snapshots=[...])` from `SnapshotRepository.list_all()`. 2 dedicated tests including ASC ordering. |
| 4 | GET /api/watchlist returns tickers | VERIFIED | `backend/app/api/watchlist.py:42-61` — `list_watchlist` returns `WatchlistResponse(entries=[...])` with `price = price_cache.get_price(...) or 0.0` (never 500s). 2 dedicated tests. |
| 5 | POST /api/watchlist adds ticker with format validation | VERIFIED | `backend/app/api/watchlist.py:69-100` — `add_watchlist_ticker` uses `WatchlistAddRequest` (1-10 letters, uppercased by validator), calls `repo.add` and `market_source.add_ticker`. 4 dedicated tests covering new, idempotent, format rejection, lowercase normalization. |
| 6 | DELETE /api/watchlist/{ticker} removes | VERIFIED | `backend/app/api/watchlist.py:108-145` — `remove_watchlist_ticker` returns 200 on success, 404 when missing. 2 dedicated tests. |
| 7 | SSE /api/stream/prices returns 200 + correct headers | VERIFIED | `backend/app/market/stream.py:76-86` — returns `StreamingResponse(media_type="text/event-stream")` with `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`, `Content-Encoding: identity`. Test `test_stream_endpoint_returns_correct_headers_and_first_events` confirms all 5 headers. |
| 8 | SSE first two lines are `retry: 1000` + `: connected` | VERIFIED | `stream.py:115-117` — yields `retry: 1000\n\n` then `: connected\n\n` first. Test confirms. |
| 9 | SSE data events include ticker/price/previous_price/timestamp/direction | VERIFIED | `stream.py:131-141` — payload is `{ticker: PriceUpdate.to_dict() for ...}`; `PriceUpdate.to_dict()` returns `ticker, price, previous_price, timestamp, change, change_percent, direction`. Direction ∈ {up, down, flat} enforced by `MarketDataSource`. Test `test_stream_payload_includes_direction_field` confirms. |
| 10 | SSE emits at ~500ms cadence, version-throttled | VERIFIED | `stream.py:24 _CADENCE_S = 0.5`, `:132-141` — only emits `data:` event when `cache.version != last_version`. Test `test_stream_version_throttling_one_event_per_bump` confirms exactly one event per `cache.update()`. |
| 11 | SSE 30s keepalive comment when dormant | VERIFIED | `stream.py:28 _KEEPALIVE_INTERVAL_S = 30.0`, `:143-147` — yields `: keepalive\n\n` when `now - last_keepalive >= 30s`. Test `test_stream_emits_keepalive_when_cache_dormant` confirms. |
| 12 | SSE graceful disconnect handling | VERIFIED | `stream.py:127-129` — `await request.is_disconnected()` checked each iteration; `:150-152` — `asyncio.CancelledError` caught and logged. 2 dedicated tests. |
| 13 | SNAP-01: 30s background loop writes snapshots | VERIFIED | `backend/app/snapshots.py:51-81` — `_snapshot_loop` writes via `SnapshotRepository().insert(total)` every `interval_seconds`; main.py:90-92 starts it with `interval_seconds=30.0`. 4 dedicated tests in `tests/snapshots/test_snapshot_loop.py` covering cadence, shutdown, error resilience, missing prices, lifespan wiring. |
| 14 | SNAP-02: trade inserts inline snapshot | VERIFIED | `portfolio.py:200-206` — after trade, computes `new_cash_dollars + positions_value` and calls `await snapshot_repo.insert(...)`. Test `test_trade_records_inline_snapshot` confirms count delta of exactly +1 per trade. |
| 15 | Health check returns 200 at /api/health | VERIFIED | `backend/app/api/system.py:12-20` — `health` returns `HealthResponse(status="ok")`. 2 dedicated tests including legacy `/health` alias. |

**Score:** 15/15 truths verified (0 present-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/api/__init__.py` | package + 3 router re-exports | VERIFIED | Exists, exports `portfolio_router`, `watchlist_router`, `system_router` |
| `backend/app/api/schemas.py` | 11 Pydantic models with validators | VERIFIED | `HealthResponse`, `TradeRequest`, `TradeResponse`, `PositionResponse`, `PortfolioResponse`, `PortfolioHistoryResponse`, `SnapshotResponse`, `WatchlistAddRequest`, `WatchlistEntry`, `WatchlistResponse`, `WatchlistMutationResponse` all present with `extra="forbid"` and `field_validator` for normalization |
| `backend/app/api/deps.py` | 7 async dependency providers | VERIFIED | `get_price_cache`, `get_market_source`, `get_user_repo`, `get_position_repo`, `get_trade_repo`, `get_snapshot_repo`, `get_watchlist_repo` |
| `backend/app/api/portfolio.py` | 3 endpoints | VERIFIED | GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history |
| `backend/app/api/watchlist.py` | 3 endpoints | VERIFIED | GET /api/watchlist, POST /api/watchlist, DELETE /api/watchlist/{ticker} |
| `backend/app/api/system.py` | 1 endpoint | VERIFIED | GET /api/health returns `{"status":"ok"}` |
| `backend/app/main.py` | Mount routers + lifespan | VERIFIED | Lines 129-134 mount SSE + 3 API routers; lines 75-76 expose `app.state.price_cache/market_source`; lines 89-93 start snapshot task; lines 99-110 shutdown sequence cancels snapshot before `close_db()`; line 137-140 keeps legacy `/health` |
| `backend/app/snapshots.py` | `start_snapshot_loop` + `_compute_total_value` | VERIFIED | Lines 31-81. Uses `asyncio.wait_for(stop_event.wait(), timeout=interval)` for bounded shutdown. Per-iteration try/except. |
| `backend/app/market/stream.py` | SSE router factory | VERIFIED | `create_stream_router(price_cache)` factory; `_KEEPALIVE_INTERVAL_S=30`, `_CADENCE_S=0.5`; version-throttled; `request.is_disconnected()` handled; `_resolve_cache` accepts instance or callable |
| `backend/tests/api/test_health.py` | 2+ test cases | VERIFIED | 2 cases: `/api/health` and legacy `/health` |
| `backend/tests/api/test_watchlist.py` | 6+ test cases | VERIFIED | 7 cases covering list/add/idempotent/format/404-remove/remove-sync |
| `backend/tests/api/test_portfolio.py` | 11+ test cases | VERIFIED | 14 cases covering initial state, buy/sell, weighted-avg, sell-to-zero, insufficient cash, sell-without-holding, validation, cache price, history ordering, empty history |
| `backend/tests/market/test_stream.py` | 6+ SSE test cases | VERIFIED | 7 cases: headers + first event, version throttling, direction field, keepalive dormant, no data on empty, disconnect exit, CancelledError handling |
| `backend/tests/snapshots/test_snapshot_loop.py` | 6+ snapshot test cases | VERIFIED | 8 cases: cash-only, position value, cadence, stop_event, insert failure, missing prices, inline trade snapshot, lifespan wiring |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `app/main.py` lifespan | `PriceCache` | `state.price_cache = PriceCache()` + `app.state.price_cache = state.price_cache` | WIRED | Line 70-76 |
| `app/main.py` lifespan | `MarketDataSource` | `create_market_data_source(state.price_cache)` + `await state.market_source.start(tickers)` | WIRED | Line 71, 85 |
| `app/main.py` lifespan | Snapshot loop | `start_snapshot_loop(state.price_cache, state._snapshot_stop, interval_seconds=30.0)` | WIRED | Line 90-92 |
| `app/main.py` shutdown | Snapshot loop | `state._snapshot_stop.set()` + `task.cancel()` + `await task` before `close_db()` | WIRED | Line 100-110, 123 |
| `app/api/portfolio.py:GET /api/portfolio` | `PriceCache.get_price` | per-position `current_price = price_cache.get_price(ticker) or 0.0` | WIRED | Line 73 |
| `app/api/portfolio.py:POST /trade` | `UserRepository.adjust_cash` | atomic `delta_cents` for buy/sell | WIRED | Line 187 |
| `app/api/portfolio.py:POST /trade` | `PositionRepository.upsert/delete` | weighted-average cost on buy, delete on sell-to-zero | WIRED | Line 191-195 |
| `app/api/portfolio.py:POST /trade` | `SnapshotRepository.insert` (SNAP-02) | inline insert of `new_cash_dollars + positions_value` | WIRED | Line 200-206 |
| `app/api/watchlist.py:POST` | `WatchlistRepository.add` + `MarketDataSource.add_ticker` | writes DB then seeds PriceCache via source | WIRED | Line 90-96 |
| `app/api/watchlist.py:DELETE` | `WatchlistRepository.remove` + `MarketDataSource.remove_ticker` | deletes DB row then evicts from PriceCache via source | WIRED | Line 127-141 |
| `app/market/stream.py:_generate_events` | `PriceCache.version` + `PriceCache.get_all` | version-throttled push | WIRED | Line 131-141 |
| `app/market/stream.py:_generate_events` | `request.is_disconnected()` | graceful disconnect (SSE-05) | WIRED | Line 127-129 |
| `app/snapshots.py:_snapshot_loop` | `UserRepository`, `PositionRepository`, `SnapshotRepository` | computes total + inserts | WIRED | Line 31-65 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `GET /api/portfolio` | `cash_balance` | `UserRepository.get()` | Yes (DB row) | FLOWING |
| `GET /api/portfolio` | `positions[].current_price` | `PriceCache.get_price(ticker)` | Yes (live simulator) | FLOWING |
| `GET /api/portfolio` | `total_value` | computed from DB + cache | Yes | FLOWING |
| `POST /api/portfolio/trade` | `current_price` | `PriceCache.get_price(ticker)` | Yes | FLOWING |
| `POST /api/portfolio/trade` | cash + position writes | `UserRepository.adjust_cash`, `PositionRepository.upsert/delete` | Yes (atomic SQLite writes) | FLOWING |
| `GET /api/portfolio/history` | `snapshots` | `SnapshotRepository.list_all()` | Yes (DB rows) | FLOWING |
| `GET /api/watchlist` | `entries[].price` | `PriceCache.get_price(row['ticker'])` or 0.0 | Yes (live) | FLOWING |
| `SSE /api/stream/prices` | `data: {...}` payload | `PriceCache.get_all()` → `PriceUpdate.to_dict()` | Yes (live updates) | FLOWING |
| `snapshot_loop` | `total_value` | DB + PriceCache | Yes | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Health alias returns ok | `curl /api/health` (via TestClient) | `200 {"status":"ok"}` | PASS |
| Legacy /health still works | `curl /health` (via TestClient) | `200 {"status":"ok"}` | PASS |
| Initial portfolio | `GET /api/portfolio` (TestClient, fresh DB) | `cash_balance=10000.0, total_value=10000.0, positions=[]` | PASS |
| Default watchlist populated | `GET /api/watchlist` | `len(entries)==10` | PASS |
| All required routes registered | `app.routes` | `['/api/health', '/api/portfolio', '/api/portfolio/history', '/api/portfolio/trade', '/api/stream/prices', '/api/watchlist', '/api/watchlist/{ticker}', '/health', ...]` | PASS |
| Full backend test suite | `pytest -q` | `142 passed, 2 warnings in 34.15s` | PASS |
| Phase-2-only test suite | `pytest tests/market/test_stream.py tests/api/ tests/snapshots/ -q` | `38 passed` | PASS |
| Lint (ruff) | `ruff check app/ tests/` | 13 pre-existing minor issues (unused imports, import sort, missing trailing newline on stream.py) — not functional, present in Phase 1 baseline | INFO |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| N/A | No phase-declared probe scripts (`scripts/*/tests/probe-*.sh`) | N/A | N/A |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| API-01 | 02-01 | GET /api/portfolio — cash, positions, total value | SATISFIED | `portfolio.py:51-101` + `test_portfolio_initial_state` + `test_portfolio_attaches_current_price_from_cache` |
| API-02 | 02-01 | POST /api/portfolio/trade — executes with validation | SATISFIED | `portfolio.py:109-215` + 5 dedicated tests (insufficient cash, insufficient shares, negative qty, invalid side, unknown ticker) |
| API-03 | 02-01 | GET /api/portfolio/history — snapshots for P&L chart | SATISFIED | `portfolio.py:223-237` + `test_portfolio_history_returns_snapshots_ordered_asc` + `test_portfolio_history_empty_when_no_trades` |
| API-04 | 02-01 | GET /api/watchlist — current watchlist with prices | SATISFIED | `watchlist.py:42-61` + `test_watchlist_lists_default_tickers` + `test_watchlist_listing_includes_added_at_and_price` |
| API-05 | 02-01 | POST /api/watchlist — adds ticker, validates format | SATISFIED | `watchlist.py:69-100` + 4 tests (new, idempotent, format, lowercase normalization) |
| API-06 | 02-01 | DELETE /api/watchlist/{ticker} — removes | SATISFIED | `watchlist.py:108-145` + `test_watchlist_remove_returns_404_when_missing` + `test_watchlist_remove_drops_ticker_and_price` |
| API-08 | 02-01 | GET /api/health — health check | SATISFIED | `system.py:12-20` + 2 tests (alias + legacy) |
| SSE-01 | 02-02 | GET /api/stream/prices — SSE, ~500ms cadence | SATISFIED | `stream.py:62-86` + `test_stream_endpoint_returns_correct_headers_and_first_events` + `test_stream_version_throttling_one_event_per_bump` |
| SSE-02 | 02-02 | Event payload: ticker, price, previous_price, timestamp, direction | SATISFIED | `stream.py:137-139` + `test_stream_payload_includes_direction_field` |
| SSE-03 | 02-02 | SSE headers: Content-Type, Cache-Control, Connection | SATISFIED | `stream.py:78-85` + `test_stream_endpoint_returns_correct_headers_and_first_events` |
| SSE-04 | 02-02 | 30s keepalive comment | SATISFIED | `stream.py:28, 143-147` + `test_stream_emits_keepalive_when_cache_dormant` |
| SSE-05 | 02-02 | Graceful disconnect handling | SATISFIED | `stream.py:127-129, 150-152` + `test_stream_exits_on_disconnect` + `test_stream_handles_cancelled_error_silently` |
| SNAP-01 | 02-03 | Background task records portfolio value every 30s | SATISFIED | `snapshots.py:51-81` + `main.py:90-92` + 4 tests (cadence, stop_event, error resilience, lifespan wiring) |
| SNAP-02 | 02-03 | Snapshot recorded immediately after each trade | SATISFIED | `portfolio.py:200-206` + `test_trade_records_inline_snapshot` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `app/market/stream.py` | 151 | Missing trailing newline (W292) | INFO | Cosmetic only; no behavioral impact. |
| Multiple | — | Pre-existing unused imports (F401), import sort (I001) | INFO | All in files outside phase 2 scope (`app/db/repositories/user.py`, `tests/db/test_repositories.py`, `app/main.py` `field` import). Ruff-clean on phase 2-specific files. |

No TBD/FIXME/XXX/HACK/PLACEHOLDER debt markers in any phase-2 file. No stub patterns (empty returns, hardcoded `{}`/`[]` flowing to render). No console.log-only handlers.

### Human Verification Required

None — all behaviors are covered by automated tests against the lifespan-installed live simulator with deterministic assertions. SSE-05 (disconnect) and SSE-04 (30s keepalive) are exercised via programmatic uvicorn + httpx with controlled timing.

### Gaps Summary

No gaps. All 15 must-haves verified against the actual codebase, 142/142 tests pass, all 14 requirement IDs (API-01..06, API-08, SSE-01..05, SNAP-01..02) have at least one passing test, and the route table shows every required endpoint at the documented path.

---

_Verified: 2026-06-27T14:40:00Z_
_Verifier: Claude (gsd-verifier)_
