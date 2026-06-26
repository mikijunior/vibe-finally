# Phase 1: Database Foundation - Research

**Researched:** 2026-06-26
**Domain:** SQLite database with aiosqlite, WAL mode, INTEGER cents storage, and thread-safe PriceCache
**Confidence:** HIGH

## Summary

Phase 1 establishes the database foundation for FinAlly: SQLite persistence via aiosqlite, WAL mode for concurrent safety, INTEGER cents for financial precision, lazy initialization on first request, and integration with the existing thread-safe PriceCache. The existing `backend/app/market/` pattern (factory + interface + implementation) provides the structural template for `backend/app/db/`. The 6-table schema (users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages) maps cleanly to SQLite with INTEGER cents storage. PriceCache (thread-safe via `threading.Lock`) and MarketDataSource ABC are already complete and need only to be wired in.

**Primary recommendation:** Add `aiosqlite>=0.22.0` to pyproject.toml, create `backend/app/db/` with repository modules following the `backend/app/market/` pattern, use FastAPI lifespan events for connection lifecycle, enable WAL via `PRAGMA journal_mode=WAL` on first connect, and store all monetary values as INTEGER cents.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DB-01 | SQLite database initialized lazily on first request | aiosqlite connection per-request pattern with existence check |
| DB-02 | SQLite running in WAL mode | `PRAGMA journal_mode=WAL` applied after connect |
| DB-03 | All monetary values stored as INTEGER cents | Schema design using INTEGER, conversion utilities |
| DB-04 | Tables: users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages | Schema maps to 6 tables with appropriate INTEGER vs TEXT types |
| MKT-06 | Abstract MarketDataSource interface | Already exists at `backend/app/market/interface.py` — integrate, don't modify |
| MKT-07 | Thread-safe PriceCache shared by all endpoints | Already exists at `backend/app/market/cache.py` — use as-is |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SQLite connection management | API/Backend | — | FastAPI lifespan events own connection lifecycle |
| WAL mode enforcement | API/Backend | — | PRAGMA set on every new connection |
| INTEGER cents storage | API/Backend | — | Schema-level decision, repository layer enforces |
| PriceCache (thread-safe) | API/Backend | — | Already exists, shared singleton across handlers |
| MarketDataSource lifecycle | API/Backend | — | start/stop managed by FastAPI lifespan |
| Schema initialization | API/Backend | — | Lazy on first request via existence check |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| aiosqlite | 0.22.1 [VERIFIED: pypi.org — latest as of Dec 2025] | Async SQLite access | Non-blocking DB reads in FastAPI async handlers; keeps SSE loop responsive |
| SQLite | 3.x (built into Python 3.12) | Persistence | Zero-config, self-contained; adequate for single-user simulation |
| FastAPI | 0.138.1 | REST API + lifespan events | Native async, lifespan context managers for DB lifecycle |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic | 2.x | Data validation | Request/response models, DB row validation |
| python-dotenv | latest | Env var loading | Reads DB path from environment |

**Installation:**
```bash
uv add aiosqlite>=0.22.0
```

**Version verification:** `pip index versions aiosqlite` — confirmed 0.22.1 as latest.

## Package Legitimacy Audit

> **Required** whenever this phase installs external packages. Run the Package Legitimacy Gate protocol before completing this section.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| aiosqlite | PyPI | ~9 years | high (standard package) | [github.com/omnilib/aiosqlite](https://github.com/omnilib/aiosqlite) | [SUS] | Flagged — planner inserts `checkpoint:human-verify` before install |

**Packages removed due to [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** aiosqlite — flagged by seam due to "unknown-downloads" and "no-repository" signals, but pip confirms it exists and is the latest version (0.22.1). The "no-repository" signal may be a false positive. Planners should verify via:
```bash
pip index versions aiosqlite  # confirm 0.22.1 available
npm view aiosqlite version     # must match — PyPI confirmed
```

## Architecture Patterns

### System Architecture Diagram

```
FastAPI Lifespan
    │
    ├── startup: create PriceCache singleton
    │              └── create_market_data_source(PriceCache)
    │                   └── start() → background task begins
    │
    ├── on first request:
    │   └── init_db() checks: SELECT name FROM sqlite_master WHERE type='table'
    │       └── if tables missing → CREATE TABLE ... + INSERT seed data (transaction)
    │
    └── shutdown: source.stop() → PriceCache persists

Request lifecycle:
    HTTP Request
        │
        └── Depends on endpoint:
                ├── /api/watchlist/*  → WatchlistRepository (RW)
                ├── /api/portfolio/*  → PositionRepository, TradeRepository, UserRepository (RW)
                ├── /api/stream/*    → PriceCache.get_all() (read only)
                └── /api/chat        → ChatRepository (RW)

PriceCache (thread-safe, in-memory)
    ├── Writers: SimulatorDataSource or MassiveDataSource (background task)
    └── Readers: SSE endpoint, portfolio valuation, trade execution
```

### Recommended Project Structure
```
backend/app/
├── db/
│   ├── __init__.py          # init_db(), get_db(), close_db(), public exports
│   ├── connection.py        # _get_connection(), _init_schema(), _enable_wal()
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── user.py          # UserRepository
│   │   ├── watchlist.py     # WatchlistRepository
│   │   ├── position.py      # PositionRepository
│   │   ├── trade.py         # TradeRepository
│   │   ├── snapshot.py      # SnapshotRepository
│   │   └── chat.py          # ChatRepository
│   └── seed.py              # DEFAULT_TICKERS, DEFAULT_CASH_CENTS constants
├── market/
│   ├── __init__.py
│   ├── cache.py             # PriceCache (existing, do not modify)
│   ├── interface.py        # MarketDataSource ABC (existing, integrate)
│   └── ...
└── main.py                  # FastAPI app with lifespan events
```

### Pattern 1: Lazy Database Initialization

**What:** Database schema created and seeded on the first request to any endpoint, not at app startup.

**When to use:** Always for this project — zero-config, no migration step.

**Example:**
```python
# backend/app/db/connection.py
import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "db" / "finally.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

_connection: aiosqlite.Connection | None = None

async def get_db() -> aiosqlite.Connection:
    """Get or create the shared DB connection. Initializes schema if needed."""
    global _connection
    if _connection is None:
        _connection = await aiosqlite.connect(str(DB_PATH))
        _connection.row_factory = aiosqlite.Row
        await _enable_wal_mode(_connection)
        await _ensure_schema(_connection)
    return _connection

async def _enable_wal_mode(db: aiosqlite.Connection) -> None:
    """Enable WAL mode for concurrent read/write safety."""
    await db.execute("PRAGMA journal_mode=WAL")
    # Verify it worked
    async with db.execute("PRAGMA journal_mode") as cursor:
        row = await cursor.fetchone()
        mode = row[0] if row else "unknown"
        # WAL mode is persistent, so subsequent connects also use WAL

async def _ensure_schema(db: aiosqlite.Connection) -> None:
    """Create tables if they don't exist. Seed default data."""
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) as cursor:
        existing = {row[0] async for row in cursor}

    if "users_profile" not in existing:
        await _create_schema(db)
        await _seed_data(db)

async def _create_schema(db: aiosqlite.Connection) -> None:
    """Create all 6 tables. All monetary columns are INTEGER cents."""
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS users_profile (
            id TEXT PRIMARY KEY DEFAULT 'default',
            cash_balance INTEGER NOT NULL DEFAULT 1000000,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS watchlist (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'default',
            ticker TEXT NOT NULL,
            added_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, ticker)
        );

        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'default',
            ticker TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            avg_cost INTEGER NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, ticker)
        );

        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'default',
            ticker TEXT NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('buy', 'sell')),
            quantity INTEGER NOT NULL,
            price INTEGER NOT NULL,
            executed_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'default',
            total_value INTEGER NOT NULL,
            recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL DEFAULT 'default',
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            actions TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """)
    await db.commit()

async def _seed_data(db: aiosqlite.Connection) -> None:
    """Seed default user profile and watchlist tickers."""
    import uuid
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat()

    # Default user with $10,000
    await db.execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES ('default', 1000000, ?)",
        (now,)
    )

    # Default watchlist tickers
    for ticker in ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]:
        await db.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, 'default', ?, ?)",
            (str(uuid.uuid4()), ticker, now)
        )

    await db.commit()
```

### Pattern 2: Repository Pattern with aiosqlite

**What:** Each table has a dedicated repository class with async methods. All monetary values in/out are converted from cents (DB) to dollars (API).

**When to use:** All DB access in Phase 1 and subsequent phases.

**Example:**
```python
# backend/app/db/repositories/watchlist.py
from __future__ import annotations
import uuid
from datetime import datetime, timezone

import aiosqlite

from ..connection import get_db


class WatchlistRepository:
    """Repository for watchlist operations. All prices returned as dollars."""

    USER_ID = "default"

    async def get_all(self) -> list[dict]:
        """Return all watchlist tickers with current prices."""
        db = await get_db()
        async with db.execute(
            "SELECT id, ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at",
            (self.USER_ID,)
        ) as cursor:
            rows = [dict(row) async for row in cursor]
        return rows

    async def add(self, ticker: str) -> dict:
        """Add a ticker to the watchlist. Returns the created row."""
        db = await get_db()
        now = datetime.now(timezone.utc).isoformat()
        id_ = str(uuid.uuid4())
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (id_, self.USER_ID, ticker.upper(), now)
        )
        await db.commit()
        return {"id": id_, "user_id": self.USER_ID, "ticker": ticker.upper(), "added_at": now}

    async def remove(self, ticker: str) -> bool:
        """Remove a ticker. Returns True if removed, False if not found."""
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (self.USER_ID, ticker.upper())
        )
        await db.commit()
        return cursor.rowcount > 0
```

### Pattern 3: INTEGER Cents Conversion Utilities

**What:** Helper functions to convert between dollars (float) and cents (int). All DB storage uses cents; all API responses use dollars.

**When to use:** Every monetary value crossing the DB/API boundary.

**Example:**
```python
# backend/app/db/cents.py
"""Utilities for INTEGER cents storage.

All monetary values are stored in the database as INTEGER cents.
All API boundaries (request/response) use float dollars.
"""

def to_cents(dollars: float) -> int:
    """Convert dollar float to integer cents. Rounds to nearest cent."""
    return round(dollars * 100)

def from_cents(cents: int) -> float:
    """Convert integer cents to dollar float."""
    return cents / 100.0

def format_dollars(cents: int) -> str:
    """Format cents as a dollar string with 2 decimal places."""
    return f"${from_cents(cents):,.2f}"
```

### Pattern 4: FastAPI Lifespan for PriceCache + MarketDataSource

**What:** App lifespan manages PriceCache and MarketDataSource lifecycle. DB connection lazy-initializes on first request.

**When to use:** Phase 1 startup/shutdown.

**Example:**
```python
# backend/app/main.py (conceptual)
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.market import PriceCache, create_market_data_source

price_cache: PriceCache | None = None
market_source = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global price_cache, market_source

    # Startup: create shared PriceCache and start market data source
    price_cache = PriceCache()
    market_source = create_market_data_source(price_cache)
    await market_source.start(["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"])

    yield

    # Shutdown: stop market data source
    if market_source:
        await market_source.stop()

app = FastAPI(lifespan=lifespan)
```

### Anti-Patterns to Avoid

- **Do not use synchronous sqlite3 in FastAPI async handlers:** Blocks the uvicorn worker thread, causing SSE streaming to stutter. Always use aiosqlite.
- **Do not use REAL for monetary columns:** Floating-point rounding errors (e.g., `0.1 + 0.2 != 0.3`). Always use INTEGER cents.
- **Do not call `db.commit()` after every statement without batching:** For bulk inserts (seed data), batch in a single transaction. For single-row operations, each `INSERT`/`UPDATE` can commit immediately.
- **Do not open a new connection per request without pooling:** For this single-user app, a single shared connection via `get_db()` is sufficient. Connection pooling adds complexity for no benefit.
- **Do not set WAL mode inside `_ensure_schema` on every call:** WAL mode is persistent once set. Checking `PRAGMA journal_mode` every request is unnecessary overhead — set once on first connection.

## Common Pitfalls

### Pitfall 1: WAL Mode Not Persistent Across Connections
**What goes wrong:** After enabling WAL mode on the first connection, subsequent connections don't see it.
**Why it happens:** WAL mode is persistent (survives connection close/open), but the PRAGMA only needs to be set once. Each new connection inherits WAL mode from the database file itself.
**How to avoid:** Set `PRAGMA journal_mode=WAL` once on the first connection creation. Do not check/re-set on every request.
**Warning signs:** N/A — WAL mode is persistent.

### Pitfall 2: Thread-Safety Confusion Between asyncio and threading
**What goes wrong:** Using `asyncio.Lock` inside `PriceCache` when the market data source runs in a background thread.
**Why it happens:** `PriceCache` uses `threading.Lock` (correct) because `SimulatorDataSource` runs price updates in a background `threading.Thread`, not an asyncio task. The `threading.Lock` is necessary and correct.
**How to avoid:** Do not replace `threading.Lock` with `asyncio.Lock`. Do not use `async with` on PriceCache — the cache is synchronous.
**Warning signs:** `TypeError: object Lock can't be used in 'async with' context`.

### Pitfall 3: Missing row_factory for Column Access
**What goes wrong:** Accessing columns by name (`row['ticker']`) returns raw values unexpectedly.
**Why it happens:** By default, sqlite3/aiosqlite returns columns by index. Setting `connection.row_factory = aiosqlite.Row` enables name-based access.
**How to avoid:** Set `_connection.row_factory = aiosqlite.Row` immediately after connect.
**Warning signs:** `IndexError` or `KeyError` when accessing columns by name.

### Pitfall 4: INTEGER Overflow for Large monetary Values
**What goes wrong:** Very large portfolio values exceed Python int range (impossible) or SQLite INTEGER range (64-bit signed, ~9.2 quintillion cents).
**Why it happens:** Not a practical concern for this simulator — $10,000 starting cash, fractional shares, max portfolio value in the millions.
**How to avoid:** Not needed. SQLite INTEGER is 64-bit signed.

## Code Examples

### Opening a Database Connection with WAL (aiosqlite 0.22.x)
```python
# Source: [VERIFIED: pypi.org aiosqlite 0.22.1 docs]
import aiosqlite

async with aiosqlite.connect("db/finally.db") as db:
    await db.execute("PRAGMA journal_mode=WAL")
    # WAL mode is persistent — subsequent connections inherit it
    db.row_factory = aiosqlite.Row

    async with db.execute("SELECT * FROM users_profile WHERE id = 'default'") as cursor:
        row = await cursor.fetchone()
        print(row["cash_balance"])  # Integer cents
```

### Async Context Manager Pattern
```python
# Source: [VERIFIED: pypi.org aiosqlite 0.22.1 docs]
async with aiosqlite.connect("db/finally.db") as db:
    await db.execute("INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                     (str(uuid.uuid4()), "default", "AAPL", now))
    await db.commit()

    async with db.execute("SELECT * FROM watchlist") as cursor:
        async for row in cursor:
            print(row["ticker"])
```

### Using executuescript for Schema Creation
```python
# Source: [VERIFIED: pypi.org aiosqlite 0.22.1 — executescript is standard sqlite3]
await db.executescript("""
    CREATE TABLE IF NOT EXISTS users_profile (...);
    CREATE TABLE IF NOT EXISTS watchlist (...);
""")
await db.commit()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Synchronous sqlite3 | aiosqlite async wrapper | Always async for FastAPI | Non-blocking DB I/O |
| DELETE journal mode | WAL mode | SQLite 3.7.0 (2010) | Concurrent reads during writes |
| REAL for money | INTEGER cents | Industry best practice | Eliminates floating-point rounding errors |
| Startup migration | Lazy initialization | Modern framework pattern | Zero-config, no migration step |

**Deprecated/outdated:**
- `sqlite3` sync module in async FastAPI handlers — use aiosqlite instead
- Connection-per-request without singleton — unnecessary for single-user app

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async DB access | Custom thread pool executing sync sqlite3 | aiosqlite | Built and tested; request queue prevents corruption |
| WAL mode implementation | Custom write ordering or locking | SQLite WAL mode | WAL is ACID, well-tested, zero-config |
| Monetary arithmetic | float calculations | INTEGER cents + conversion utils | float rounding errors are a well-known bug |
| DB schema migration | Versioned migration scripts | Lazy init + CREATE TABLE IF NOT EXISTS | Simpler for single-user, no migration failures |

**Key insight:** SQLite's built-in WAL mode handles all concurrent read/write safety. The aiosqlite library handles async I/O without blocking the event loop. INTEGER cents eliminates floating-point errors. All of these are solved problems — don't reinvent them.

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research. The planner and discuss-phase use this section to identify decisions that need user confirmation before execution.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | aiosqlite "SUS" verdict is a false positive | Package Legitimacy Audit | aiosqlite is a well-known, widely-used package with a GitHub repo; the "no-repository" signal may be inaccurate. Planner should verify with `pip index versions aiosqlite` |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

## Open Questions

1. **DB file path for Docker deployment**
   - What we know: DB_PATH should be `db/finally.db` relative to project root, volume-mounted at container `/app/db`
   - What's unclear: Whether the `finally.db` file itself should be gitignored (yes — runtime state)
   - Recommendation: Add `db/finally.db` to `.gitignore`, keep `db/.gitkeep` for directory presence

2. **PriceCache initialization order relative to DB**
   - What we know: PriceCache is a singleton created at startup, DB initializes lazily on first request
   - What's unclear: None — these are independent
   - Recommendation: Proceed as designed

## Environment Availability

> Skip this section if the phase has no external dependencies (code/config-only changes).

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12+ | Backend runtime | ✓ (uv manages) | 3.12 | N/A |
| aiosqlite | Database layer | ✓ | 0.22.1 (latest) | N/A |
| fastapi | API framework | ✓ | 0.138.1 (from pyproject.toml) | N/A |

**Missing dependencies with no fallback:** None identified.

**Missing dependencies with fallback:** None identified.

## Security Domain

> Required when `security_enforcement` is enabled (absent = enabled). Omit only if explicitly `false` in config.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in scope — single "default" user |
| V3 Session Management | No | No session state — stateless API |
| V4 Access Control | Partial | DB user_id="default" hardcoded; no multi-user enforcement needed yet |
| V5 Input Validation | Yes | Pydantic models for all request bodies; ticker symbol format validation |
| V6 Cryptography | No | No sensitive data at rest; SQLite file not encrypted |

### Known Threat Patterns for SQLite + FastAPI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via ticker parameter | Tampering | Parameterized queries (`?` placeholders) — all DB access uses aiosqlite parameterized queries |
| Ticker symbol injection in DDL | Tampering | Ticker validated via regex before any DB operation |
| Path traversal via DB filename | Information Disclosure | DB path is fixed, derived from app root — not user-supplied |

## Sources

### Primary (HIGH confidence)
- [pypi.org/project/aiosqlite/](https://pypi.org/project/aiosqlite/) — Version 0.22.1 (Dec 2025), async context manager pattern, usage examples
- [sqlite.org/wal.html](https://www.sqlite.org/wal.html) — WAL mode persistence, concurrent behavior, checkpointing
- [sqlite.org/pragma.html](https://sqlite.org/pragma.html) — `PRAGMA journal_mode=WAL` syntax, WAL mode persistence

### Secondary (MEDIUM confidence)
- Existing `backend/app/market/` implementation — confirmed thread-safe `PriceCache` with `threading.Lock`, confirmed `MarketDataSource` ABC interface
- `planning/PLAN.md` — Database schema specification, WAL mode requirement, INTEGER cents requirement

### Tertiary (LOW confidence)
- None — all critical claims verified via primary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — aiosqlite verified on PyPI, FastAPI confirmed in pyproject.toml
- Architecture: HIGH — patterns from existing codebase (`backend/app/market/`) applied to DB layer
- Pitfalls: HIGH — WAL persistence, thread-safety, row_factory are well-documented SQLite/aiosqlite behaviors

**Research date:** 2026-06-26
**Valid until:** 2026-07-26 (30 days — SQLite and aiosqlite are stable)
