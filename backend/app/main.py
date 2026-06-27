"""FastAPI application entry point for FinAlly.

Manages the lifecycle of PriceCache, MarketDataSource, and database
via FastAPI lifespan events. Provides integration between the SQLite
watchlist and the live market data system.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI

from app.api import portfolio_router, system_router, watchlist_router
from app.db import close_db, init_db
from app.db.repositories import WatchlistRepository
from app.db.seed import DEFAULT_TICKERS
from app.market import (
    MarketDataSource,
    PriceCache,
    create_market_data_source,
    create_stream_router,
)
from app.snapshots import start_snapshot_loop


@dataclass
class AppState:
    """Application-level shared state managed by the lifespan."""

    price_cache: PriceCache | None = None
    market_source: MarketDataSource | None = None
    snapshot_task: asyncio.Task | None = None
    _snapshot_stop: asyncio.Event | None = None


# Module-level singleton so test code can access and reset state
state = AppState()


def _get_cache() -> PriceCache:
    """Return the current PriceCache from app state."""
    cache = state.price_cache
    if cache is None:
        raise RuntimeError("PriceCache not yet initialized")
    return cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage PriceCache, MarketDataSource, and DB lifecycle.

    Startup order:
        1. init_db() — lazy schema + seed on first request
        2. Create PriceCache singleton
        3. Create MarketDataSource via factory
        4. Load watchlist from DB and start source with those tickers

    Shutdown order:
        1. Stop MarketDataSource
        2. Close DB connection
        3. Clear state
    """
    # Startup
    await init_db()

    state.price_cache = PriceCache()
    state.market_source = create_market_data_source(state.price_cache)

    # Expose shared singletons on app.state so API dependencies can resolve
    # them via `request.app.state` regardless of test overrides.
    app.state.price_cache = state.price_cache
    app.state.market_source = state.market_source

    # Load current watchlist from DB; fall back to defaults if empty
    repo = WatchlistRepository()
    watchlist_rows = await repo.get_all()
    tickers = [row["ticker"] for row in watchlist_rows]
    if not tickers:
        tickers = list(DEFAULT_TICKERS)

    await state.market_source.start(tickers)

    # Start the snapshot loop AFTER the market source is up so the loop
    # sees live prices from its first iteration onward (SNAP-01).
    state._snapshot_stop = asyncio.Event()
    state.snapshot_task = start_snapshot_loop(
        state.price_cache, state._snapshot_stop, interval_seconds=30.0
    )
    app.state.snapshot_stop = state._snapshot_stop

    yield

    # Shutdown
    # Stop the snapshot loop BEFORE closing the DB so the in-flight insert
    # (if any) doesn't race with close_db().
    if getattr(state, "_snapshot_stop", None) is not None:
        state._snapshot_stop.set()
    task = getattr(state, "snapshot_task", None)
    if task is not None and not task.done():
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    state.snapshot_task = None
    state._snapshot_stop = None

    if state.market_source is not None:
        await state.market_source.stop()
        state.market_source = None

    if state.price_cache is not None:
        state.price_cache = None

    app.state.price_cache = None
    app.state.market_source = None
    app.state.snapshot_stop = None

    await close_db()


app = FastAPI(title="FinAlly", version="0.1.0", lifespan=lifespan)

# Mount SSE stream router using a callable to avoid the import-time None problem
app.include_router(create_stream_router(_get_cache))

# Mount REST API routers (system first, then alphabetical by feature)
app.include_router(system_router)
app.include_router(watchlist_router)
app.include_router(portfolio_router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


if os.environ.get("TESTING") == "1":
    import asyncio

    @app.get("/cache/state")
    async def cache_state():
        """Debug endpoint: return current cache state. TESTING=1 only."""
        cache = state.price_cache
        if cache is None:
            return {"tickers": [], "count": 0}
        return {
            "tickers": sorted(cache.get_all().keys()),
            "count": len(cache),
        }

    @app.post("/watchlist/test-add/{ticker}")
    async def test_add_ticker(ticker: str):
        """Test endpoint: add ticker to watchlist and sync cache/source."""
        repo = WatchlistRepository()
        row = await repo.add(ticker)
        if state.market_source is not None:
            await state.market_source.add_ticker(row["ticker"])
        return {"added": row}

    @app.post("/watchlist/test-remove/{ticker}")
    async def test_remove_ticker(ticker: str):
        """Test endpoint: remove ticker from watchlist and sync cache/source."""
        repo = WatchlistRepository()
        removed = await repo.remove(ticker)
        if removed:
            if state.market_source is not None:
                await state.market_source.remove_ticker(ticker.upper())
            if state.price_cache is not None:
                state.price_cache.remove(ticker.upper())
        return {"removed": removed, "ticker": ticker.upper()}
