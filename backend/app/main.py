"""FastAPI application entry point for FinAlly.

Manages the lifecycle of PriceCache, MarketDataSource, and database
via FastAPI lifespan events. Provides integration between the SQLite
watchlist and the live market data system.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from fastapi import FastAPI

from app.db import close_db, init_db
from app.db.repositories import WatchlistRepository
from app.db.seed import DEFAULT_TICKERS
from app.market import (
    MarketDataSource,
    PriceCache,
    create_market_data_source,
    create_stream_router,
)


@dataclass
class AppState:
    """Application-level shared state managed by the lifespan."""

    price_cache: PriceCache | None = None
    market_source: MarketDataSource | None = None


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

    # Load current watchlist from DB; fall back to defaults if empty
    repo = WatchlistRepository()
    watchlist_rows = await repo.get_all()
    tickers = [row["ticker"] for row in watchlist_rows]
    if not tickers:
        tickers = list(DEFAULT_TICKERS)

    await state.market_source.start(tickers)
    yield

    # Shutdown
    if state.market_source is not None:
        await state.market_source.stop()
        state.market_source = None

    if state.price_cache is not None:
        state.price_cache = None

    await close_db()


app = FastAPI(title="FinAlly", version="0.1.0", lifespan=lifespan)

# Mount SSE stream router using a callable to avoid the import-time None problem
app.include_router(create_stream_router(_get_cache))


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
