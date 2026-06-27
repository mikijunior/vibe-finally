"""Portfolio REST endpoints.

Three endpoints:

- ``GET  /api/portfolio``        — current positions + cash + total value
- ``POST /api/portfolio/trade``  — execute a market order with validation
- ``GET  /api/portfolio/history``— portfolio value snapshots over time
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_position_repo,
    get_price_cache,
    get_snapshot_repo,
    get_trade_repo,
    get_user_repo,
)
from app.api.schemas import (
    PortfolioHistoryResponse,
    PortfolioResponse,
    PositionResponse,
    SnapshotResponse,
    TradeRequest,
    TradeResponse,
)
from app.db.cents import from_cents, to_cents
from app.db.repositories import (
    PositionRepository,
    SnapshotRepository,
    TradeRepository,
    UserRepository,
)
from app.market.cache import PriceCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


# ---------------------------------------------------------------------------
# GET /api/portfolio
# ---------------------------------------------------------------------------


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    position_repo: Annotated[PositionRepository, Depends(get_position_repo)],
    price_cache: Annotated[PriceCache, Depends(get_price_cache)],
) -> PortfolioResponse:
    """Return current portfolio snapshot: cash, positions with P&L, total value."""
    user = await user_repo.get()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not initialized",
        )

    positions = await position_repo.get_all()

    pos_responses: list[PositionResponse] = []
    positions_value = 0.0
    for pos in positions:
        ticker = pos["ticker"]
        quantity = float(pos["quantity"])
        avg_cost = float(pos["avg_cost"])
        current_price = price_cache.get_price(ticker) or 0.0

        if avg_cost > 0:
            unrealized_pnl = (current_price - avg_cost) * quantity
            pnl_percent = (current_price - avg_cost) / avg_cost * 100.0
        else:
            unrealized_pnl = 0.0
            pnl_percent = 0.0

        positions_value += quantity * current_price
        pos_responses.append(
            PositionResponse(
                ticker=ticker,
                quantity=quantity,
                avg_cost=avg_cost,
                current_price=current_price,
                unrealized_pnl=unrealized_pnl,
                pnl_percent=pnl_percent,
            )
        )

    cash_balance = float(user["cash_balance"])
    total_value = cash_balance + positions_value

    return PortfolioResponse(
        cash_balance=cash_balance,
        positions=pos_responses,
        total_value=total_value,
    )


# ---------------------------------------------------------------------------
# POST /api/portfolio/trade
# ---------------------------------------------------------------------------


@router.post("/trade", response_model=TradeResponse)
async def execute_trade(
    request: TradeRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    position_repo: Annotated[PositionRepository, Depends(get_position_repo)],
    trade_repo: Annotated[TradeRepository, Depends(get_trade_repo)],
    snapshot_repo: Annotated[SnapshotRepository, Depends(get_snapshot_repo)],
    price_cache: Annotated[PriceCache, Depends(get_price_cache)],
) -> TradeResponse:
    """Execute a market order with validation, atomic cash adjust, and snapshot.

    Validation order:
        1. Current price must exist in cache (ticker known to simulator)
        2. Buy: cash sufficient for ``price * quantity``
           Sell: position exists with ``quantity >= requested``
        3. Cash and shares updated atomically (single connection)
        4. Trade row recorded; portfolio snapshot recorded inline
    """
    ticker = request.ticker
    side = request.side
    quantity = float(request.quantity)

    current_price = price_cache.get_price(ticker)
    if current_price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"No live price for {ticker}; add to watchlist first "
                "or wait for first tick"
            ),
        )

    user = await user_repo.get()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not initialized",
        )

    existing_position = await position_repo.get_one(ticker)

    if side == "buy":
        cost_cents = to_cents(current_price * quantity)
        cash_balance_cents = to_cents(float(user["cash_balance"]))
        if cash_balance_cents < cost_cents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient cash: need ${cost_cents / 100:.2f}, "
                    f"have ${cash_balance_cents / 100:.2f}"
                ),
            )
        delta_cents = -cost_cents

        if existing_position is None:
            new_qty = quantity
            new_avg_cost = current_price
        else:
            existing_qty = float(existing_position["quantity"])
            existing_avg = float(existing_position["avg_cost"])
            new_qty = existing_qty + quantity
            new_avg_cost = (existing_avg * existing_qty + current_price * quantity) / new_qty
    else:  # sell
        if existing_position is None or float(existing_position["quantity"]) < quantity:
            have = float(existing_position["quantity"]) if existing_position else 0.0
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Insufficient shares for {ticker}: need {quantity}, have {have}"
                ),
            )
        delta_cents = to_cents(current_price * quantity)
        existing_qty = float(existing_position["quantity"])
        existing_avg = float(existing_position["avg_cost"])
        new_qty = existing_qty - quantity
        new_avg_cost = existing_avg  # unchanged on sell

    # Mutate cash atomically
    new_cash_cents = await user_repo.adjust_cash(delta_cents)
    new_cash_dollars = from_cents(new_cash_cents)

    # Mutate positions
    if new_qty > 0:
        # Round avg_cost back to cents to avoid float drift in DB
        await position_repo.upsert(ticker, new_qty, round(new_avg_cost, 2))
    else:
        await position_repo.delete(ticker)

    # Record trade
    trade_row = await trade_repo.insert(ticker, side, quantity, current_price)

    # Record post-trade snapshot (inline). Uses fresh cash + all position
    # mark-to-market against the current price cache.
    all_positions_after = await position_repo.get_all()
    positions_value = 0.0
    for p in all_positions_after:
        positions_value += float(p["quantity"]) * (price_cache.get_price(p["ticker"]) or 0.0)
    await snapshot_repo.insert(new_cash_dollars + positions_value)

    # Reload post-trade position (may be None if sold to zero)
    post_position = await position_repo.get_one(ticker)

    return TradeResponse(
        trade=trade_row,
        position=post_position,
        cash_balance=new_cash_dollars,
    )


# ---------------------------------------------------------------------------
# GET /api/portfolio/history
# ---------------------------------------------------------------------------


@router.get("/history", response_model=PortfolioHistoryResponse)
async def get_portfolio_history(
    snapshot_repo: Annotated[SnapshotRepository, Depends(get_snapshot_repo)],
) -> PortfolioHistoryResponse:
    """Return all portfolio value snapshots, oldest first (ASC by recorded_at)."""
    rows = await snapshot_repo.list_all()
    snapshots = [
        SnapshotResponse(
            id=row["id"],
            total_value=float(row["total_value"]),
            recorded_at=row["recorded_at"],
        )
        for row in rows
    ]
    return PortfolioHistoryResponse(snapshots=snapshots)
