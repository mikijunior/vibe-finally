"""Tests for ``app.llm.context.build_portfolio_context``.

Uses the real repositories against a fresh test DB (via the
``fresh_db`` fixture from ``tests.conftest``) and a real ``PriceCache``
populated with synthetic prices.
"""

from __future__ import annotations

import pytest

from app.db.repositories import (
    ChatRepository,
    PositionRepository,
    TradeRepository,
    UserRepository,
    WatchlistRepository,
)
from app.llm.context import build_portfolio_context
from app.market.cache import PriceCache


@pytest.fixture
def price_cache_with_prices() -> PriceCache:
    """A fresh PriceCache populated with 3 tickers used in the tests."""
    cache = PriceCache()
    cache.update("AAPL", 190.0)
    cache.update("GOOGL", 175.0)
    cache.update("MSFT", 420.0)
    return cache


async def test_build_portfolio_context_includes_required_keys(
    fresh_db, price_cache_with_prices
):
    """The returned dict has all required top-level keys."""
    user_repo = UserRepository()
    position_repo = PositionRepository()
    trade_repo = TradeRepository()
    watchlist_repo = WatchlistRepository()

    # Seed a user with $10,000 cash (the default seeder already does this on init,
    # but be explicit so the test is self-contained.)
    user = await user_repo.get()
    assert user is not None

    context = await build_portfolio_context(
        price_cache_with_prices,
        user_repo,
        position_repo,
        trade_repo,
        watchlist_repo,
    )

    assert "cash_balance_dollars" in context
    assert "total_value_dollars" in context
    assert "positions" in context
    assert "watchlist" in context
    assert "recent_trades" in context


async def test_build_portfolio_context_attaches_current_price(
    fresh_db, price_cache_with_prices
):
    """Each position row carries current_price from PriceCache and the computed P&L."""
    user_repo = UserRepository()
    position_repo = PositionRepository()
    trade_repo = TradeRepository()
    watchlist_repo = WatchlistRepository()

    # Insert a position directly: 2 shares of AAPL at $180 avg_cost.
    await position_repo.upsert("AAPL", 2.0, 180.0)

    context = await build_portfolio_context(
        price_cache_with_prices,
        user_repo,
        position_repo,
        trade_repo,
        watchlist_repo,
    )

    assert len(context["positions"]) == 1
    pos = context["positions"][0]
    assert pos["ticker"] == "AAPL"
    assert pos["quantity"] == 2.0
    assert pos["avg_cost"] == 180.0
    assert pos["current_price"] == 190.0
    assert pos["unrealized_pnl"] == pytest.approx((190.0 - 180.0) * 2.0)
    # (10 / 180) * 100 ~= 5.555...
    assert pos["pnl_percent"] == pytest.approx((10.0 / 180.0) * 100.0)


async def test_build_portfolio_context_includes_recent_trades(
    fresh_db, price_cache_with_prices
):
    """Recent trades show up under recent_trades with all expected fields."""
    user_repo = UserRepository()
    position_repo = PositionRepository()
    trade_repo = TradeRepository()
    watchlist_repo = WatchlistRepository()

    # Insert three trades so list_recent(limit=5) returns 3 rows.
    await trade_repo.insert("AAPL", "buy", 2.0, 180.0)
    await trade_repo.insert("GOOGL", "buy", 1.0, 170.0)
    await trade_repo.insert("MSFT", "sell", 1.0, 410.0)

    context = await build_portfolio_context(
        price_cache_with_prices,
        user_repo,
        position_repo,
        trade_repo,
        watchlist_repo,
    )

    assert len(context["recent_trades"]) == 3
    for trade in context["recent_trades"]:
        assert "ticker" in trade
        assert "side" in trade
        assert "quantity" in trade
        assert "price" in trade
        assert "executed_at" in trade


async def test_build_portfolio_context_watchlist_attaches_price(
    fresh_db, price_cache_with_prices
):
    """Each watchlist row carries the live price from PriceCache (0.0 if unknown)."""
    user_repo = UserRepository()
    position_repo = PositionRepository()
    trade_repo = TradeRepository()
    watchlist_repo = WatchlistRepository()

    # Default seed tickers are loaded by init_db; AAPL is one of them.
    rows = await watchlist_repo.get_all()
    tickers = {row["ticker"] for row in rows}
    assert "AAPL" in tickers

    context = await build_portfolio_context(
        price_cache_with_prices,
        user_repo,
        position_repo,
        trade_repo,
        watchlist_repo,
    )

    aapl = next((w for w in context["watchlist"] if w["ticker"] == "AAPL"), None)
    assert aapl is not None
    assert aapl["price"] == 190.0


async def test_build_portfolio_context_total_value_includes_cash_and_positions(
    fresh_db, price_cache_with_prices
):
    """total_value_dollars = cash + sum(price * qty) for all positions."""
    user_repo = UserRepository()
    position_repo = PositionRepository()
    trade_repo = TradeRepository()
    watchlist_repo = WatchlistRepository()

    user = await user_repo.get()
    cash = float(user["cash_balance"])

    await position_repo.upsert("AAPL", 2.0, 180.0)
    await position_repo.upsert("MSFT", 1.0, 400.0)

    context = await build_portfolio_context(
        price_cache_with_prices,
        user_repo,
        position_repo,
        trade_repo,
        watchlist_repo,
    )

    expected = cash + 2.0 * 190.0 + 1.0 * 420.0
    assert context["total_value_dollars"] == pytest.approx(expected)
    assert context["cash_balance_dollars"] == pytest.approx(cash)
    # Ensure the ChatRepository is importable from the same package path
    assert ChatRepository is not None
