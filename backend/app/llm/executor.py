"""Execute LLM-returned trades and watchlist changes.

Reuses the same validation as ``app/api/portfolio.py`` and
``app/api/watchlist.py``. Per-action errors are captured and returned in
``ExecutionResult`` without aborting the batch.

Public surface:

- ``ExecutorRepos`` — bundle of repositories + price cache + market source
- ``execute_actions(response, repos)`` — apply trades + watchlist changes
- ``ExecutionResult``, ``TradeActionResult``, ``WatchlistActionResult`` — result types
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from app.db.cents import from_cents, to_cents
from app.db.repositories import (
    PositionRepository,
    SnapshotRepository,
    TradeRepository,
    UserRepository,
    WatchlistRepository,
)
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource

from .schemas import ChatResponse, TradeAction, WatchlistChange

logger = logging.getLogger(__name__)


@dataclass
class TradeActionResult:
    """Per-action outcome of an auto-executed trade."""

    type: str = "trade"
    ticker: str = ""
    side: Optional[str] = None
    quantity: Optional[float] = None
    status: str = "executed"
    detail: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "ticker": self.ticker,
            "side": self.side,
            "quantity": self.quantity,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass
class WatchlistActionResult:
    """Per-action outcome of an auto-executed watchlist change."""

    type: str = "watchlist"
    ticker: str = ""
    action: Optional[str] = None
    status: str = "executed"
    detail: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "ticker": self.ticker,
            "action": self.action,
            "status": self.status,
            "detail": self.detail,
        }


@dataclass
class ExecutionResult:
    """Aggregate outcome of an ``execute_actions`` call."""

    actions: list = field(default_factory=list)

    def to_list(self) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self.actions]


@dataclass
class ExecutorRepos:
    """Bundle of repository, cache, and source dependencies for the executor."""

    user_repo: UserRepository
    position_repo: PositionRepository
    trade_repo: TradeRepository
    watchlist_repo: WatchlistRepository
    snapshot_repo: SnapshotRepository
    price_cache: PriceCache
    market_source: MarketDataSource | None = None


async def _execute_one_trade(
    action: TradeAction, repos: ExecutorRepos
) -> TradeActionResult:
    """Apply a single trade through the same validation rules as /api/portfolio/trade."""
    ticker = action.ticker.upper()
    side = action.side
    quantity = float(action.quantity)

    current_price = repos.price_cache.get_price(ticker)
    if current_price is None:
        return TradeActionResult(
            ticker=ticker,
            side=side,
            quantity=quantity,
            status="failed",
            detail=(
                f"No live price for {ticker}; add to watchlist first "
                "or wait for first tick"
            ),
        )

    user = await repos.user_repo.get()
    if user is None:
        return TradeActionResult(
            ticker=ticker,
            side=side,
            quantity=quantity,
            status="failed",
            detail="User profile not initialized",
        )

    existing_position = await repos.position_repo.get_one(ticker)

    if side == "buy":
        cost_cents = to_cents(current_price * quantity)
        cash_balance_cents = to_cents(float(user["cash_balance"]))
        if cash_balance_cents < cost_cents:
            return TradeActionResult(
                ticker=ticker,
                side="buy",
                quantity=quantity,
                status="failed",
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
            return TradeActionResult(
                ticker=ticker,
                side="sell",
                quantity=quantity,
                status="failed",
                detail=f"Insufficient shares for {ticker}: need {quantity}, have {have}",
            )
        delta_cents = to_cents(current_price * quantity)
        existing_qty = float(existing_position["quantity"])
        existing_avg = float(existing_position["avg_cost"])
        new_qty = existing_qty - quantity
        new_avg_cost = existing_avg  # unchanged on sell

    # Mutate cash atomically.
    new_cash_cents = await repos.user_repo.adjust_cash(delta_cents)
    new_cash_dollars = from_cents(new_cash_cents)

    # Mutate positions.
    if new_qty > 0:
        await repos.position_repo.upsert(ticker, new_qty, round(new_avg_cost, 2))
    else:
        await repos.position_repo.delete(ticker)

    # Record trade.
    await repos.trade_repo.insert(ticker, side, quantity, current_price)

    # Inline snapshot.
    all_positions_after = await repos.position_repo.get_all()
    positions_value = 0.0
    for p in all_positions_after:
        positions_value += float(p["quantity"]) * (repos.price_cache.get_price(p["ticker"]) or 0.0)
    await repos.snapshot_repo.insert(new_cash_dollars + positions_value)

    return TradeActionResult(
        ticker=ticker,
        side=side,
        quantity=quantity,
        status="executed",
        detail=None,
    )


async def _execute_one_watchlist_change(
    change: WatchlistChange, repos: ExecutorRepos
) -> WatchlistActionResult:
    """Apply a single watchlist mutation. Mirrors ``app/api/watchlist.py`` semantics."""
    ticker = change.ticker.upper()
    action = change.action

    if action == "add":
        if await repos.watchlist_repo.exists(ticker):
            return WatchlistActionResult(
                ticker=ticker,
                action="add",
                status="executed",
                detail="already on watchlist",
            )
        await repos.watchlist_repo.add(ticker)
        if repos.market_source is not None:
            try:
                await repos.market_source.add_ticker(ticker)
            except Exception as exc:  # noqa: BLE001 - defensive
                logger.warning(
                    "market_source.add_ticker(%s) failed: %s", ticker, exc
                )
        return WatchlistActionResult(
            ticker=ticker,
            action="add",
            status="executed",
            detail=None,
        )

    # remove
    removed = await repos.watchlist_repo.remove(ticker)
    if not removed:
        return WatchlistActionResult(
            ticker=ticker,
            action="remove",
            status="failed",
            detail=f"Ticker {ticker} not on watchlist",
        )
    if repos.market_source is not None:
        try:
            await repos.market_source.remove_ticker(ticker)
        except Exception as exc:  # noqa: BLE001 - defensive
            logger.warning(
                "market_source.remove_ticker(%s) failed: %s", ticker, exc
            )
    return WatchlistActionResult(
        ticker=ticker,
        action="remove",
        status="executed",
        detail=None,
    )


async def execute_actions(
    response: ChatResponse, repos: ExecutorRepos
) -> ExecutionResult:
    """Execute all trades and watchlist changes in a ``ChatResponse``.

    Failures are captured PER ACTION and appended to ``result.actions``;
    one bad action does not abort the batch.
    """
    result = ExecutionResult(actions=[])

    for trade in response.trades:
        try:
            result.actions.append(await _execute_one_trade(trade, repos))
        except Exception as exc:  # noqa: BLE001 - defensive: never poison the batch
            logger.exception("trade action crashed")
            result.actions.append(
                TradeActionResult(
                    ticker=trade.ticker.upper(),
                    side=trade.side,
                    quantity=float(trade.quantity),
                    status="failed",
                    detail=f"internal error: {exc!s}",
                )
            )

    for change in response.watchlist_changes:
        try:
            result.actions.append(await _execute_one_watchlist_change(change, repos))
        except Exception as exc:  # noqa: BLE001
            logger.exception("watchlist action crashed")
            result.actions.append(
                WatchlistActionResult(
                    ticker=change.ticker.upper(),
                    action=change.action,
                    status="failed",
                    detail=f"internal error: {exc!s}",
                )
            )

    return result


__all__ = [
    "TradeActionResult",
    "WatchlistActionResult",
    "ExecutionResult",
    "ExecutorRepos",
    "execute_actions",
]
