# Phase 1: Database Foundation - Context

**Gathered:** 2026-06-26
**Status:** Ready for planning

<domain>
## Phase Boundary

SQLite database layer with lazy initialization, WAL mode, INTEGER cents storage, and thread-safe price cache. Produces: DB schema in `backend/app/db/`, repository layer, connection management, seed data, and integration with existing `PriceCache` and `MarketDataSource` interface.
</domain>

<decisions>
## Implementation Decisions

### Database Architecture
- **D-01:** Use `aiosqlite` for all SQLite operations — non-blocking DB access keeps FastAPI async handlers and SSE streaming responsive
- **D-02:** Repository pattern — `backend/app/db/repositories/` with modules for each table (`user.py`, `watchlist.py`, `position.py`, `trade.py`, `snapshot.py`, `chat.py`)
- **D-03:** DB module lives at `backend/app/db/` following the established `backend/app/market/` pattern — `__init__.py` exports public interface
- **D-04:** `backend/app/db/__init__.py` exposes `init_db()`, `get_db()`, `close_db()` — lifecycle managed by FastAPI lifespan events
- **D-05:** All monetary values stored as `INTEGER` cents — `DB-03` requirement, prevents floating-point rounding errors
- **D-06:** WAL mode enabled via `PRAGMA journal_mode=WAL` — `DB-02` requirement, enables concurrent read/write safety

### Seed Data
- **D-07:** User profile: `id="default"`, `cash_balance=1000000` cents ($10,000.00) — INTEGER storage
- **D-08:** Default watchlist tickers: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

### Lazy Initialization
- **D-09:** Database initialized on first request to any endpoint — no blocking startup, no separate migration step
- **D-10:** Check `SELECT name FROM sqlite_master WHERE type='table'` — if tables missing, run schema + seed in one transaction

### PriceCache Integration
- **D-11:** `PriceCache` already exists at `backend/app/market/cache.py` with thread-safe `_lock`, `update()`, `get_all()` — no changes needed
- **D-12:** `MarketDataSource` interface already exists at `backend/app/market/interface.py` — Phase 1 integrates it, does not modify it

### Existing Code Insights

### Reusable Assets
- `backend/app/market/cache.py` `PriceCache` — already thread-safe via `threading.Lock`, used as-is
- `backend/app/market/interface.py` `MarketDataSource` ABC — existing interface, Phase 1 wires it to DB-backed tickers
- `backend/app/market/__init__.py` exports — `PriceUpdate`, `PriceCache`, `MarketDataSource`, `create_market_data_source`, `create_stream_router`
- `backend/pyproject.toml` already includes `aiosqlite` as a dependency to add

### Established Patterns
- Factory pattern for market data (`backend/app/market/factory.py`) — DB initialization can follow similar factory/dependency-injection pattern
- `__init__.py` public API pattern in `backend/app/market/` — same pattern for `backend/app/db/`
- asyncio-compatible — all DB operations must be `async def` to integrate with FastAPI async handlers

### Integration Points
- `PriceCache` reads prices from market data; watchlist CRUD in Phase 1 adds/removes tickers from both DB and `PriceCache`
- `MarketDataSource.add_ticker()` / `remove_ticker()` will call DB watchlist to persist changes
- Phase 2 REST endpoints import from `backend/app/db/` repositories

</code_context>

<specifics>
## Specific Ideas

No external references or "build it like X" moments — this is a pure infrastructure phase with requirements fully captured in ROADMAP.md and PLAN.md.
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope
</deferred>

<canonical_refs>
## Canonical References

### Product Specification
- `planning/PLAN.md` — Database schema, lazy init, WAL mode, INTEGER cents, seed data, all defined here
- `planning/MARKET_DATA_SUMMARY.md` — Market data completed component summary; `PriceCache` and `MarketDataSource` interface documented here

### Implementation
- `backend/app/market/__init__.py` — Public API: `PriceUpdate`, `PriceCache`, `MarketDataSource`, `create_market_data_source`, `create_stream_router`
- `backend/app/market/cache.py` — Existing `PriceCache` implementation (thread-safe, `update()`, `get_all()`, `version`)
- `backend/app/market/interface.py` — `MarketDataSource` ABC contract
- `backend/app/market/factory.py` — Factory pattern for market data source creation (reference for DB factory pattern)
- `backend/pyproject.toml` — Python project config; add `aiosqlite` dependency here

### Research
- `planning/research/STACK.md` — aiosqlite confirmed as correct async SQLite choice
- `planning/research/ARCHITECTURE.md` — Three-layer backend architecture (REST handlers → service layer → data access layer)
- `planning/research/PITFALLS.md` — SQLite WAL mode requirement, INTEGER cents for financial math, blocking uvicorn workers risk

</canonical_refs>

---

*Phase: 1-Database Foundation*
*Context gathered: 2026-06-26*
