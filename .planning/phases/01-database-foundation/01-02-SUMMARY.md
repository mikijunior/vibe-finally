---
phase: 01-database-foundation
plan: "02"
status: complete
subsystem: backend
tags:
  - database
  - repositories
  - sqlite
  - aiosqlite
  - cents
dependency_graph:
  requires: []
  provides:
    - backend/app/db/cents.py
    - backend/app/db/repositories/
    - backend/tests/db/test_repositories.py
  affects: []
tech_stack:
  added:
    - aiosqlite (already in pyproject.toml from 01-01)
  patterns:
    - Repository pattern: one class per DB table, async methods
    - INTEGER cents conversion at API boundary
    - Parameterized SQL queries (no f-string interpolation)
key_files:
  created:
    - backend/app/db/cents.py
    - backend/app/db/repositories/__init__.py
    - backend/app/db/repositories/user.py
    - backend/app/db/repositories/watchlist.py
    - backend/app/db/repositories/position.py
    - backend/app/db/repositories/trade.py
    - backend/app/db/repositories/snapshot.py
    - backend/app/db/repositories/chat.py
    - backend/tests/db/test_repositories.py
decisions:
  - id: D-02
    description: Repository pattern — one async class per DB table in backend/app/db/repositories/
  - id: D-05
    description: All monetary values stored as INTEGER cents; API boundary uses float dollars
metrics:
  duration_minutes: "<1"
  completed_date: "2026-06-26"
  tasks_completed: 1
  files_created: 9
---

# Phase 01 Plan 02: Repository Layer Summary

## One-liner

Async repository layer with 6 data-access modules and INTEGER cents storage, fully tested.

## What Was Built

### `backend/app/db/cents.py`
- `to_cents(dollars: float) -> int`: Converts dollar float to integer cents via `round(dollars * 100)`
- `from_cents(cents: int) -> float`: Converts cents back to dollars via `cents / 100.0`
- `format_dollars(cents: int) -> str`: Formats cents as `$1,234.56` string
- Round-trip identity property verified: `to_cents(from_cents(c)) == c` for all integer cents

### Six Repository Modules

| Module | Class | Key Methods |
|--------|-------|-------------|
| `user.py` | `UserRepository` | `get()`, `update_cash(dollars)`, `adjust_cash(delta_cents)` |
| `watchlist.py` | `WatchlistRepository` | `get_all()`, `add(ticker)`, `remove(ticker)`, `exists(ticker)` |
| `position.py` | `PositionRepository` | `get_all()`, `get_one(ticker)`, `upsert(ticker, qty, avg_cost_dollars)`, `delete(ticker)` |
| `trade.py` | `TradeRepository` | `insert(ticker, side, qty, price_dollars)`, `list_all()`, `list_recent(limit)` |
| `snapshot.py` | `SnapshotRepository` | `insert(total_value_dollars)`, `list_all()` |
| `chat.py` | `ChatRepository` | `insert(role, content, actions)`, `list_all()`, `list_recent(limit)` |

All monetary values (cash_balance, avg_cost, price, total_value) cross the API boundary as dollars but are stored as INTEGER cents. Quantity columns are stored as plain integer shares.

All SQL uses parameterized `?` placeholders — no f-string SQL injection possible.

### Test Suite: `backend/tests/db/test_repositories.py`
25 pytest-asyncio test cases covering:
- Cents round-trip identity (7 parametrized cases)
- `format_dollars` formatting
- `UserRepository`: get with cents conversion, update_cash writes cents, adjust_cash returns new cents
- `WatchlistRepository`: 10 seed tickers, uppercase normalization, idempotent add, remove true/false
- `PositionRepository`: upsert stores cents, get_one returns None when missing, delete returns true
- `TradeRepository`: insert stores price as cents, list_recent orders descending
- `SnapshotRepository`: insert stores total_value as cents, list_all orders ascending
- `ChatRepository`: actions dict JSON round-trip, NULL actions handled correctly

## Deviations from Plan

None — plan executed as written. The `exists()` method was added to `WatchlistRepository` as required by the plan but missing from the pre-existing partial implementation. The `__init__.py` was also expanded from 1 export to all 6.

## Verification Results

- `pytest tests/db/test_repositories.py -v`: **25 passed** in 0.07s
- `pytest tests/market -q`: **73 passed** in 0.94s (no regressions)
- `grep -rn 'f"SELECT|f"INSERT|f"UPDATE|f"DELETE' backend/app/db/repositories/`: **0 matches** (no f-string SQL)
- `grep -c 'REAL' backend/app/db/schema.sql`: **0** (no REAL money columns)
- All 6 repository classes importable: `from app.db.repositories import UserRepository, WatchlistRepository, PositionRepository, TradeRepository, SnapshotRepository, ChatRepository` — **OK**

## Threat Model Compliance

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-01-03 (SQL injection) | All queries use `?` parameterized placeholders | Mitigated |
| T-01-04 (ticker injection) | `WatchlistRepository.add` normalizes to uppercase | Mitigated |
| T-01-05 (cents precision leak) | `format_dollars` and `from_cents` are public by design | Accepted |
| T-01-06 (no audit on insert) | `datetime('now')` auto-populates timestamps | Accepted |

## Self-Check: PASSED

All files exist, commit hash `0f9b88a` verified in git history, all 25 tests pass, all 6 repos importable, no f-string SQL, no REAL money columns, existing market tests still pass.

## Commits

- `0f9b88a` feat(01-02): build repository layer with INTEGER cents storage
