---
phase: 02-backend-api-sse-streaming
plan: 01
subsystem: api
tags: [fastapi, pydantic, sqlite, rest, pytest-asyncio, dependency-injection]

# Dependency graph
requires:
  - phase: 01-database-foundation
    provides: aiosqlite repositories (User/Position/Trade/Snapshot/Watchlist), thread-safe PriceCache, MarketDataSource interface, lifespan startup wiring
provides:
  - REST API surface under /api/portfolio, /api/watchlist, /api/health with full request/response validation
  - Pydantic schemas for trade, portfolio, watchlist, snapshot responses
  - FastAPI dependency providers wiring repos and shared singletons
  - Test suite (23 API tests) covering happy paths, validation, and integration with the live simulator
affects: [phase-02-plan-02-sse, phase-02-plan-03-snapshots, phase-03-llm-chat, phase-04-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns: [lazy router imports in api/__init__.py, request.app.state for testable singletons, INTEGER cents in DB + dollars on wire, atomic cash adjust with aiosqlite, weighted-average cost in route handler, Pydantic field_validator for input normalization (not Field pattern)]

key-files:
  created:
    - backend/app/api/__init__.py
    - backend/app/api/schemas.py
    - backend/app/api/deps.py
    - backend/app/api/portfolio.py
    - backend/app/api/watchlist.py
    - backend/app/api/system.py
    - backend/tests/api/__init__.py
    - backend/tests/api/test_health.py
    - backend/tests/api/test_watchlist.py
    - backend/tests/api/test_portfolio.py
  modified:
    - backend/app/main.py
    - backend/tests/conftest.py

key-decisions:
  - "Pydantic field_validator chosen over Field(pattern=...) for ticker/side so case normalization happens before pattern check (BUY → buy is invalid as a pattern but valid after normalization)"
  - "Lazy router imports in app/api/__init__.py via __getattr__ — allows incremental package construction without all router modules present"
  - "Watchlist handlers do NOT call PriceCache.update / remove directly — MarketDataSource.add_ticker / remove_ticker owns cache state per the simulator contract"
  - "Trade execution validates ticker presence in PriceCache before any DB write — no 'phantom' orders allowed"
  - "Portfolio snapshot inserted inline after every successful trade (in addition to the 30-second background task from plan 02-03)"
  - "Seeded_client fixture waits up to 2s for len(price_cache) >= 10 so trade tests have live prices; cleans up non-default tickers on teardown"
  - "Legacy /health endpoint preserved (unchanged) for backward compatibility with Phase 1 lifespan tests; /api/health is the new public alias"

patterns-established:
  - "Repo dependency pattern: each handler depends on Fresh repo instances via get_*_repo deps — repos are stateless aside from the shared aiosqlite connection"
  - "Cache-derived pricing: portfolio P&L and watchlist prices come from PriceCache.get_price, defaulting to 0.0 on cache miss (never 500)"
  - "Atomic cash adjust: adjust_cash returns new raw cents via SELECT after UPDATE on same connection — race-free for single-process aiosqlite"
  - "Inline snapshot at trade time: trade handler computes total_value as cash + mark-to-market of all positions, inserts one snapshot row, then returns"

requirements-completed: [API-01, API-02, API-03, API-04, API-05, API-06, API-08]

coverage:
  - id: D1
    description: "GET /api/portfolio returns cash_balance, positions with current_price/unrealized_pnl/pnl_percent from PriceCache, total_value"
    requirement: API-01
    verification:
      - kind: unit
        ref: tests/api/test_portfolio.py#test_portfolio_initial_state
        status: pass
      - kind: unit
        ref: tests/api/test_portfolio.py#test_portfolio_attaches_current_price_from_cache
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /api/portfolio/trade validates ticker/quantity/side before any DB write; rejects insufficient cash and insufficient shares with 400, invalid input with 422"
    requirement: API-02
    verification:
      - kind: unit
        ref: tests/api/test_portfolio.py#test_trade_rejects_buy_with_insufficient_cash
        status: pass
      - kind: unit
        ref: tests/api/test_portfolio.py#test_trade_rejects_sell_without_holding
        status: pass
      - kind: unit
        ref: tests/api/test_portfolio.py#test_trade_rejects_negative_quantity
        status: pass
      - kind: unit
        ref: tests/api/test_portfolio.py#test_trade_rejects_invalid_side
        status: pass
      - kind: unit
        ref: tests/api/test_portfolio.py#test_trade_rejects_unknown_ticker
        status: pass
    human_judgment: false
  - id: D3
    description: "Successful buy decrements cash by to_cents(price*qty), inserts trades row, upserts positions with weighted-average avg_cost"
    requirement: API-03
    verification:
      - kind: unit
        ref: tests/api/test_portfolio.py#test_trade_buy_decrements_cash_and_creates_position
        status: pass
      - kind: unit
        ref: tests/api/test_portfolio.py#test_trade_buy_uses_weighted_average_cost
        status: pass
    human_judgment: false
  - id: D4
    description: "Successful sell credits cash, inserts trades row, decrements position quantity (or deletes row if reaches 0)"
    requirement: API-04
    verification:
      - kind: unit
        ref: tests/api/test_portfolio.py#test_trade_sell_updates_position_and_credits_cash
        status: pass
      - kind: unit
        ref: tests/api/test_portfolio.py#test_trade_sell_to_zero_deletes_position
        status: pass
    human_judgment: false
  - id: D5
    description: "GET /api/portfolio/history returns portfolio_snapshots ordered ASC by recorded_at"
    requirement: API-05
    verification:
      - kind: unit
        ref: tests/api/test_portfolio.py#test_portfolio_history_returns_snapshots_ordered_asc
        status: pass
      - kind: unit
        ref: tests/api/test_portfolio.py#test_portfolio_history_empty_when_no_trades
        status: pass
    human_judgment: false
  - id: D6
    description: "GET /api/watchlist returns tickers with current PriceCache price (0.0 if not yet seen); never 500s on missing tickers"
    requirement: API-06
    verification:
      - kind: unit
        ref: tests/api/test_watchlist.py#test_watchlist_lists_default_tickers
        status: pass
      - kind: unit
        ref: tests/api/test_watchlist.py#test_watchlist_listing_includes_added_at_and_price
        status: pass
    human_judgment: false
  - id: D7
    description: "POST /api/watchlist validates ticker format (1-10 letters), persists via repo, calls market_source.add_ticker; idempotent on duplicate"
    requirement: API-08
    verification:
      - kind: unit
        ref: tests/api/test_watchlist.py#test_watchlist_add_new_ticker
        status: pass
      - kind: unit
        ref: tests/api/test_watchlist.py#test_watchlist_add_is_idempotent
        status: pass
      - kind: unit
        ref: tests/api/test_watchlist.py#test_watchlist_add_rejects_invalid_format
        status: pass
      - kind: unit
        ref: tests/api/test_watchlist.py#test_watchlist_add_uppercases_lowercase_ticker
        status: pass
    human_judgment: false
  - id: D8
    description: "DELETE /api/watchlist/{ticker} returns 404 when missing, 200 on success; syncs to market_source and PriceCache"
    requirement: API-08
    verification:
      - kind: unit
        ref: tests/api/test_watchlist.py#test_watchlist_remove_returns_404_when_missing
        status: pass
      - kind: unit
        ref: tests/api/test_watchlist.py#test_watchlist_remove_drops_ticker_and_price
        status: pass
    human_judgment: false

# Metrics
duration: 128 min
completed: 2026-06-27
status: complete
---

# Phase 02 Plan 01: REST API Surface Summary

**REST API surface for FinAlly: portfolio snapshot, market-order execution with weighted-average cost, portfolio history, watchlist CRUD with MarketDataSource/PriceCache sync, and a public `/api/health` alias.**

## Performance

- **Duration:** 128 min
- **Started:** 2026-06-27T11:05:05Z
- **Completed:** 2026-06-27T13:13:12Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments

- Built `app/api/` package with three FastAPI routers (portfolio, watchlist, system) and 9 Pydantic v2 models
- Trade execution enforces cash/share sufficiency with atomic cash adjust and weighted-average cost
- Every successful trade inserts a row in `trades` AND a row in `portfolio_snapshots` (inline)
- Watchlist handlers route through `MarketDataSource.add_ticker` / `remove_ticker` so PriceCache stays consistent
- Test suite covers 23 cases (2 health + 7 watchlist + 14 portfolio); all 127 backend tests pass; ruff is clean

## Task Commits

1. **Task 1: Create api package skeleton, Pydantic schemas, and dependency providers** - `7a96d6e` (feat)
2. **Task 2: Implement portfolio + watchlist + system routers and mount them in main.py** - `edb8735` (feat)
3. **Task 3: Write pytest-asyncio tests for the three routers** - `0d8f32b` (test)

## Files Created/Modified

### Created

- `/Users/mijunior/vibecode/finally/backend/app/api/__init__.py` — Package marker with lazy router re-exports
- `/Users/mijunior/vibecode/finally/backend/app/api/schemas.py` — 9 Pydantic v2 request/response models (Health, Trade, Position, Portfolio, Snapshot, Watchlist)
- `/Users/mijunior/vibecode/finally/backend/app/api/deps.py` — 7 FastAPI dependency providers (price_cache, market_source, 5 repos)
- `/Users/mijunior/vibecode/finally/backend/app/api/portfolio.py` — GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history
- `/Users/mijunior/vibecode/finally/backend/app/api/watchlist.py` — GET /api/watchlist, POST /api/watchlist, DELETE /api/watchlist/{ticker}
- `/Users/mijunior/vibecode/finally/backend/app/api/system.py` — GET /api/health
- `/Users/mijunior/vibecode/finally/backend/tests/api/__init__.py` — Package marker
- `/Users/mijunior/vibecode/finally/backend/tests/api/test_health.py` — 2 cases
- `/Users/mijunior/vibecode/finally/backend/tests/api/test_watchlist.py` — 7 cases
- `/Users/mijunior/vibecode/finally/backend/tests/api/test_portfolio.py` — 14 cases

### Modified

- `/Users/mijunior/vibecode/finally/backend/app/main.py` — Mounted three routers; populated `app.state.price_cache` and `app.state.market_source` in lifespan
- `/Users/mijunior/vibecode/finally/backend/tests/conftest.py` — Added fresh_db, testing_env, client, seeded_client fixtures

## Decisions Made

1. **Pydantic `field_validator` instead of `Field(pattern=...)`** — Pattern constraints run before field validators, so accepting `BUY` and normalizing to `buy` requires validation logic that runs after normalization. Using `field_validator` for ticker/side validation (with `isalpha()` / membership checks) gives clean 422 errors with helpful messages.

2. **Lazy router imports via `__getattr__`** — `app/api/__init__.py` imports routers lazily so the package is importable during incremental development (e.g., importing schemas before all router modules exist). The trade-off: minor indirection cost, but enables faster iteration.

3. **Watchlist handlers delegate cache mutations to `MarketDataSource`** — Per the simulator contract, `MarketDataSource.add_ticker` already seeds PriceCache with the seed price, and `remove_ticker` evicts from PriceCache. Calling `PriceCache.update` / `remove` directly from the watchlist handler would duplicate logic and risk drift. Defensive try/except wraps the source call so DB success still returns 200 even if the source has a transient error.

4. **Inline portfolio snapshot at trade time** — The trade handler computes post-trade total_value (cash + mark-to-market of all positions) and inserts a `portfolio_snapshots` row inline. This gives immediate P&L points for the frontend without waiting for the 30-second background snapshot task from plan 02-03.

5. **`seeded_client` fixture waits for live prices** — Without this wait, `price_cache.get_price(ticker)` returns None and trades return 400 instead of succeeding. The fixture polls `len(price_cache) >= 10` for up to 2s (40 × 50ms) and cleans up non-default tickers on teardown so tests don't pollute each other.

6. **Legacy `/health` endpoint preserved** — Phase 1 tests already probe `/health` for backward compatibility. Adding `/api/health` as a new public alias without removing the legacy endpoint keeps the migration additive and risk-free.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing validation] Pydantic pattern constraint ran before field validator**
- **Found during:** Task 1
- **Issue:** `Field(pattern=r"^(buy|sell)$")` validated input BEFORE `field_validator` could lowercase it; `BUY` was rejected with 422 even though it's semantically valid
- **Fix:** Replaced `Field(pattern=...)` with `field_validator` that normalizes then validates membership in `{"buy", "sell"}`. Same for ticker (uses `.isalpha()` instead of regex). Same Pydantic 422 semantics, but allows normalization.
- **Files modified:** `backend/app/api/schemas.py`
- **Commit:** 7a96d6e

**2. [Rule 1 - Bug] Package __init__.py imports broken until Task 2 lands**
- **Found during:** Task 1 (during verification)
- **Issue:** Eager `from .portfolio import router` in `__init__.py` caused `ModuleNotFoundError` while the routers were being written incrementally
- **Fix:** Made router imports lazy via `__getattr__` so `app.api.schemas` and `app.api.deps` can be imported standalone (useful for test isolation and incremental development)
- **Files modified:** `backend/app/api/__init__.py`
- **Commit:** 7a96d6e

None - no plan deviations, all tasks executed exactly as written otherwise.

## Verification Results

All verification gates from the plan passed:

1. Task 2 automated check: **ALL CHECKS PASSED** (14 sequential assertions across health, watchlist, portfolio endpoints)
2. `pytest -q tests/api/ -v`: **23 passed in 1.09s**
3. `pytest -q` (full backend suite): **127 passed in 2.05s** (no regressions)
4. Route listing confirms `/api/health`, `/api/portfolio`, `/api/portfolio/trade`, `/api/portfolio/history`, `/api/watchlist`, `/api/watchlist/{ticker}`, `/api/stream/prices`, legacy `/health` all registered
5. `ruff check app/api tests/api`: **All checks passed**

## Self-Check: PASSED

- All created files exist on disk
- All commit hashes (`7a96d6e`, `edb8735`, `0d8f32b`) present in git log
- All requirements (API-01, API-02, API-03, API-04, API-05, API-06, API-08) covered by passing tests