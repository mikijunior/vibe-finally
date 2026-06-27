"""Watchlist REST endpoints.

Three endpoints:

- ``GET    /api/watchlist``            — list tickers with latest prices
- ``POST   /api/watchlist``            — add ticker (DB + MarketDataSource + PriceCache)
- ``DELETE /api/watchlist/{ticker}``   — remove ticker (DB + MarketDataSource + PriceCache)
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_market_source,
    get_price_cache,
    get_watchlist_repo,
)
from app.api.schemas import (
    WatchlistAddRequest,
    WatchlistEntry,
    WatchlistMutationResponse,
    WatchlistResponse,
)
from app.db.repositories import WatchlistRepository
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


# ---------------------------------------------------------------------------
# GET /api/watchlist
# ---------------------------------------------------------------------------


@router.get("", response_model=WatchlistResponse)
async def list_watchlist(
    repo: Annotated[WatchlistRepository, Depends(get_watchlist_repo)],
    price_cache: Annotated[PriceCache, Depends(get_price_cache)],
) -> WatchlistResponse:
    """Return the current watchlist with latest price for each ticker.

    Tickers without a known price (simulator hasn't ticked yet) report 0.0
    rather than 500-ing — the frontend can still render a row.
    """
    rows = await repo.get_all()
    entries = [
        WatchlistEntry(
            ticker=row["ticker"],
            added_at=row["added_at"],
            price=price_cache.get_price(row["ticker"]) or 0.0,
        )
        for row in rows
    ]
    return WatchlistResponse(entries=entries)


# ---------------------------------------------------------------------------
# POST /api/watchlist
# ---------------------------------------------------------------------------


@router.post("", response_model=WatchlistMutationResponse)
async def add_watchlist_ticker(
    request: WatchlistAddRequest,
    repo: Annotated[WatchlistRepository, Depends(get_watchlist_repo)],
    market_source: Annotated[MarketDataSource | None, Depends(get_market_source)],
) -> WatchlistMutationResponse:
    """Add a ticker to the watchlist and sync to MarketDataSource + PriceCache.

    Idempotent: if the ticker is already present, returns 200 with
    ``already_present=true`` without touching the data source. The actual
    source-side seed (PriceCache) is handled by ``MarketDataSource.add_ticker``
    per the simulator implementation; we do not call ``PriceCache.update``
    here.
    """
    ticker = request.ticker

    if await repo.exists(ticker):
        return WatchlistMutationResponse(
            ticker=ticker, action="added", already_present=True
        )

    await repo.add(ticker)

    if market_source is not None:
        try:
            await market_source.add_ticker(ticker)
        except Exception:  # pragma: no cover - defensive: source can have transient errors
            logger.exception("MarketDataSource.add_ticker(%s) failed; DB write succeeded", ticker)

    return WatchlistMutationResponse(
        ticker=ticker, action="added", already_present=False
    )


# ---------------------------------------------------------------------------
# DELETE /api/watchlist/{ticker}
# ---------------------------------------------------------------------------


@router.delete("/{ticker}", response_model=WatchlistMutationResponse)
async def remove_watchlist_ticker(
    ticker: str,
    repo: Annotated[WatchlistRepository, Depends(get_watchlist_repo)],
    market_source: Annotated[MarketDataSource | None, Depends(get_market_source)],
) -> WatchlistMutationResponse:
    """Remove a ticker from the watchlist and sync to MarketDataSource + PriceCache.

    Returns 404 if the ticker is not present. The actual cache eviction is
    handled by ``MarketDataSource.remove_ticker`` per the simulator
    implementation; we do not call ``PriceCache.remove`` here.
    """
    normalized = ticker.strip().upper()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ticker path param must not be empty",
        )

    removed = await repo.remove(normalized)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticker {normalized} not on watchlist",
        )

    if market_source is not None:
        try:
            await market_source.remove_ticker(normalized)
        except Exception:  # pragma: no cover - defensive
            logger.exception(
                "MarketDataSource.remove_ticker(%s) failed; DB delete succeeded",
                normalized,
            )

    return WatchlistMutationResponse(
        ticker=normalized, action="removed", already_present=False
    )
