"""FastAPI dependency providers for the REST API.

Each provider returns a fresh repository instance per request (repositories
are stateless aside from the shared aiosqlite connection inside ``get_db``).
Price cache and market source come from ``request.app.state`` so tests can
swap them via ``app.state`` mutation without re-importing modules.
"""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.db.repositories import (
    ChatRepository,
    PositionRepository,
    SnapshotRepository,
    TradeRepository,
    UserRepository,
    WatchlistRepository,
)
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource


async def get_price_cache(request: Request) -> PriceCache:
    """Return the active ``PriceCache`` from ``app.state``.

    Raises 503 if the cache has not been initialized (lifespan did not run).
    """
    cache: PriceCache | None = getattr(request.app.state, "price_cache", None)
    if cache is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PriceCache not initialized",
        )
    return cache


async def get_market_source(request: Request) -> MarketDataSource | None:
    """Return the active ``MarketDataSource`` (or ``None`` in tests)."""
    return getattr(request.app.state, "market_source", None)


async def get_user_repo() -> UserRepository:
    """Return a fresh ``UserRepository`` (stateless aside from the DB connection)."""
    return UserRepository()


async def get_position_repo() -> PositionRepository:
    """Return a fresh ``PositionRepository``."""
    return PositionRepository()


async def get_trade_repo() -> TradeRepository:
    """Return a fresh ``TradeRepository``."""
    return TradeRepository()


async def get_snapshot_repo() -> SnapshotRepository:
    """Return a fresh ``SnapshotRepository``."""
    return SnapshotRepository()


async def get_watchlist_repo() -> WatchlistRepository:
    """Return a fresh ``WatchlistRepository``."""
    return WatchlistRepository()


async def get_chat_repo() -> ChatRepository:
    """Return a fresh ``ChatRepository``."""
    return ChatRepository()
