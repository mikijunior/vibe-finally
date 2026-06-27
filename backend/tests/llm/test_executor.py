"""Tests for the LLM executor module.

The executor auto-applies ``ChatResponse.trades`` and
``ChatResponse.watchlist_changes`` to the user's portfolio. It must reuse
the same validation rules as ``app/api/portfolio.py`` and
``app/api/watchlist.py`` — failures are captured PER ACTION and never abort
the batch.
"""

from __future__ import annotations

import pytest

from app.db.repositories import (
    PositionRepository,
    TradeRepository,
    UserRepository,
    WatchlistRepository,
)
from app.llm.executor import (
    ExecutionResult,
    ExecutorRepos,
    TradeActionResult,
    WatchlistActionResult,
    execute_actions,
)
from app.llm.schemas import ChatResponse, TradeAction, WatchlistChange
import app.main as main


@pytest.fixture
async def seeded_repos(seeded_client):
    """Return an ``ExecutorRepos`` bound to the live lifespan state.

    Waits for the simulator to populate at least 10 tickers so trade tests
    have live prices. Returns fresh repository instances each call.
    """
    cache = main.state.price_cache
    market_source = main.state.market_source

    return ExecutorRepos(
        user_repo=UserRepository(),
        position_repo=PositionRepository(),
        trade_repo=TradeRepository(),
        watchlist_repo=WatchlistRepository(),
        snapshot_repo=__import__(
            "app.db.repositories", fromlist=["SnapshotRepository"]
        ).SnapshotRepository(),
        price_cache=cache,
        market_source=market_source,
    )


@pytest.mark.asyncio
async def test_executor_buy_success(seeded_repos):
    """Buying a single share of AAPL decreases cash and inserts a position row."""
    response = ChatResponse(
        message="ok",
        trades=[TradeAction(ticker="AAPL", side="buy", quantity=1)],
        watchlist_changes=[],
    )
    result = await execute_actions(response, seeded_repos)
    assert isinstance(result, ExecutionResult)
    assert len(result.actions) == 1

    action = result.actions[0]
    assert isinstance(action, TradeActionResult)
    assert action.type == "trade"
    assert action.ticker == "AAPL"
    assert action.side == "buy"
    assert action.quantity == 1.0
    assert action.status == "executed"
    assert action.detail is None

    # Side-effects: cash decreased, position inserted, trade row recorded,
    # snapshot inserted.
    user = await seeded_repos.user_repo.get()
    assert user["cash_balance"] < 10000.0
    position = await seeded_repos.position_repo.get_one("AAPL")
    assert position is not None
    assert float(position["quantity"]) == 1.0
    trades = await seeded_repos.trade_repo.list_all()
    assert len(trades) == 1
    assert trades[0]["ticker"] == "AAPL"
    snapshots = await seeded_repos.snapshot_repo.list_all()
    # Snapshot may include the seeded "default" row plus our post-trade row.
    assert len(snapshots) >= 1


@pytest.mark.asyncio
async def test_executor_buy_insufficient_cash(seeded_repos):
    """A buy with quantity 99999 fails per-action and leaves cash untouched."""
    response = ChatResponse(
        message="ok",
        trades=[TradeAction(ticker="AAPL", side="buy", quantity=99999)],
        watchlist_changes=[],
    )
    result = await execute_actions(response, seeded_repos)
    assert len(result.actions) == 1
    action = result.actions[0]
    assert action.status == "failed"
    assert "Insufficient cash" in (action.detail or "")

    # Cash unchanged.
    user = await seeded_repos.user_repo.get()
    assert user["cash_balance"] == 10000.0

    # No position row, no trade row.
    position = await seeded_repos.position_repo.get_one("AAPL")
    assert position is None
    trades = await seeded_repos.trade_repo.list_all()
    assert len(trades) == 0


@pytest.mark.asyncio
async def test_executor_sell_without_position(seeded_repos):
    """A sell when the user holds 0 shares of AAPL fails per-action."""
    response = ChatResponse(
        message="ok",
        trades=[TradeAction(ticker="AAPL", side="sell", quantity=1)],
        watchlist_changes=[],
    )
    result = await execute_actions(response, seeded_repos)
    assert len(result.actions) == 1
    action = result.actions[0]
    assert action.status == "failed"
    assert "Insufficient shares" in (action.detail or "")

    # Cash unchanged.
    user = await seeded_repos.user_repo.get()
    assert user["cash_balance"] == 10000.0


@pytest.mark.asyncio
async def test_executor_watchlist_add_success(seeded_repos):
    """Adding a new ticker to the watchlist persists the row."""
    response = ChatResponse(
        message="ok",
        trades=[],
        watchlist_changes=[WatchlistChange(ticker="PYPL", action="add")],
    )
    result = await execute_actions(response, seeded_repos)
    assert len(result.actions) == 1
    action = result.actions[0]
    assert isinstance(action, WatchlistActionResult)
    assert action.type == "watchlist"
    assert action.ticker == "PYPL"
    assert action.action == "add"
    assert action.status == "executed"

    exists = await seeded_repos.watchlist_repo.exists("PYPL")
    assert exists is True


@pytest.mark.asyncio
async def test_executor_watchlist_remove_missing(seeded_repos):
    """Removing a ticker not on the watchlist yields a per-action failure."""
    response = ChatResponse(
        message="ok",
        trades=[],
        watchlist_changes=[WatchlistChange(ticker="ZZZZ", action="remove")],
    )
    result = await execute_actions(response, seeded_repos)
    assert len(result.actions) == 1
    action = result.actions[0]
    assert action.status == "failed"
    assert "not on watchlist" in (action.detail or "")


@pytest.mark.asyncio
async def test_executor_partial_failure_does_not_abort(seeded_repos):
    """A failing trade does NOT prevent the subsequent watchlist add from running."""
    response = ChatResponse(
        message="ok",
        trades=[TradeAction(ticker="AAPL", side="buy", quantity=99999)],
        watchlist_changes=[WatchlistChange(ticker="PYPL", action="add")],
    )
    result = await execute_actions(response, seeded_repos)
    assert len(result.actions) == 2
    assert result.actions[0].status == "failed"
    assert result.actions[1].status == "executed"
    assert result.actions[1].type == "watchlist"
    assert result.actions[1].ticker == "PYPL"

    # Watchlist add actually persisted.
    assert await seeded_repos.watchlist_repo.exists("PYPL") is True


@pytest.mark.asyncio
async def test_executor_no_live_price(seeded_repos):
    """A trade on a ticker with no live price yields a per-action failure."""
    response = ChatResponse(
        message="ok",
        trades=[TradeAction(ticker="UNKN", side="buy", quantity=1)],
        watchlist_changes=[],
    )
    result = await execute_actions(response, seeded_repos)
    assert len(result.actions) == 1
    action = result.actions[0]
    assert action.status == "failed"
    assert "No live price" in (action.detail or "")


@pytest.mark.asyncio
async def test_executor_to_list_serializes_results(seeded_repos):
    """``ExecutionResult.to_list()`` returns dicts compatible with the chat response."""
    response = ChatResponse(
        message="ok",
        trades=[TradeAction(ticker="AAPL", side="buy", quantity=1)],
        watchlist_changes=[],
    )
    result = await execute_actions(response, seeded_repos)
    serialized = result.to_list()
    assert len(serialized) == 1
    assert serialized[0]["type"] == "trade"
    assert serialized[0]["status"] == "executed"
    assert serialized[0]["ticker"] == "AAPL"
    assert serialized[0]["side"] == "buy"
    assert serialized[0]["quantity"] == 1.0