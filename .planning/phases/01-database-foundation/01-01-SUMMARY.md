---
phase: 01-database-foundation
plan: "01"
subsystem: database
tags: [sqlite, aiosqlite, backend, database-foundation]
dependency_graph:
  requires: []
  provides: [DB-01, DB-04]
  affects: [01-02, 01-03, 02-rest-api]
tech_stack:
  added: [aiosqlite 0.22.1]
  patterns: [lazy-singleton, wal-mode, integer-cents]
key_files:
  created:
    - backend/app/db/__init__.py
    - backend/app/db/connection.py
    - backend/app/db/schema.sql
    - backend/app/db/seed.py
  modified:
    - backend/pyproject.toml
    - backend/uv.lock
decisions:
  - "WAL mode via PRAGMA journal_mode=WAL on first connection only — persists for subsequent connections"
  - "Double-checked locking with asyncio.Lock for thread-safe lazy singleton"
  - "DB_PATH derived from Path(__file__).resolve().parents[3].parent / 'db' / 'finally.db'"
  - "schema.sql read as text and executed via executescript on first connect"
  - "seed.py is idempotent — skips INSERT if users_profile row already exists"
metrics:
  duration: "~5 minutes"
  completed: "2026-06-26"
  tasks_completed: 1
  tasks_total: 1
  files_created: 4
  files_modified: 2
status: complete
---

# Phase 01 Plan 01: Database Foundation Summary

## One-liner

Shipped the `backend/app/db/` package with lazy SQLite initialization, WAL mode, and the 6-table schema using INTEGER cents for all monetary columns.

## What Was Built

### Files Created

**`backend/app/db/schema.sql`** — All 6 `CREATE TABLE IF NOT EXISTS` statements:
- `users_profile` (id, cash_balance INTEGER, created_at)
- `watchlist` (id, user_id, ticker, added_at, UNIQUE user+ticker)
- `positions` (id, user_id, ticker, quantity INTEGER, avg_cost INTEGER, updated_at)
- `trades` (id, user_id, ticker, side CHECK buy/sell, quantity INTEGER, price INTEGER cents, executed_at)
- `portfolio_snapshots` (id, user_id, total_value INTEGER cents, recorded_at)
- `chat_messages` (id, user_id, role CHECK user/assistant, content, actions JSON, created_at)

Header comment notes: "Monetary values stored as INTEGER cents. Quantity columns are integer share counts."

**`backend/app/db/seed.py`** — Module-level constants:
```python
DEFAULT_USER_ID = "default"
DEFAULT_CASH_CENTS = 1_000_000  # $10,000.00
DEFAULT_TICKERS = ("AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX")
```

**`backend/app/db/connection.py`** — Lazy singleton with WAL:
- `_project_root()` helper computes project root from `Path(__file__).resolve().parents[3].parent`
- `DB_PATH = _project_root() / "db" / "finally.db"`
- `_connection: aiosqlite.Connection | None = None` (module-level singleton)
- `_init_lock = asyncio.Lock()` for thread-safe double-checked locking
- `_enable_wal(db)` — executes `PRAGMA journal_mode=WAL` and verifies result
- `_ensure_schema(db)` — checks if `users_profile` exists; if not, reads `schema.sql` and runs `executescript`
- `_seed_defaults(db)` — inserts default user (1000000 cents) and 10 tickers; idempotent via SELECT check
- `get_db()` — public lazy accessor with double-checked locking
- `init_db()` — public wrapper returning connection
- `close_db()` — closes connection and resets singleton

**`backend/app/db/__init__.py`** — Public re-exports:
```python
from .connection import init_db, get_db, close_db
__all__ = ["init_db", "get_db", "close_db"]
```

### Files Modified

**`backend/pyproject.toml`** — Added `aiosqlite>=0.22.0` to dependencies (sorted before fastapi).

**`backend/uv.lock`** — Refreshed via `uv lock`, resolved to aiosqlite v0.22.1.

## Verification Results

| Check | Result |
|-------|--------|
| All 6 tables created on first `init_db()` | PASS |
| WAL mode active (`PRAGMA journal_mode = wal`) | PASS |
| Default user cash_balance = 1000000 cents | PASS |
| All 10 default tickers seeded in watchlist | PASS |
| Second `init_db()` returns same connection (idempotent) | PASS |
| No re-seed on second call (watchlist count = 10) | PASS |
| INTEGER columns in schema.sql: 7 | PASS (≥5 required) |
| REAL columns in schema.sql: 0 | PASS |
| Existing pytest tests (73) | PASS |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| — | — | No new trust boundary surface introduced; DB path derived from fixed app location, not user input |

## Self-Check

- [x] `backend/app/db/__init__.py` exposes `init_db`, `get_db`, `close_db`
- [x] `backend/app/db/schema.sql` defines all 6 tables with INTEGER cents
- [x] `backend/app/db/seed.py` declares `DEFAULT_USER_ID`, `DEFAULT_CASH_CENTS`, `DEFAULT_TICKERS`
- [x] `backend/app/db/connection.py` exposes async lifecycle functions with WAL mode
- [x] `backend/pyproject.toml` includes `aiosqlite>=0.22.0`
- [x] `uv.lock` refreshed (aiosqlite v0.22.1)
- [x] All automated verification checks pass
- [x] Existing pytest suite passes (73 tests)

## Commit

`589099b` — `feat(01-01): add aiosqlite dependency and backend/app/db package`
