"""Tests for the repository layer and cents conversion utilities."""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

# Patch DB_PATH before importing app modules
import app.db.connection as connection


@pytest.fixture(autouse=True)
def fresh_db():
    """Reset DB state before each test, creating a fresh temp DB."""
    tmp = tempfile.mkdtemp()
    connection.DB_PATH = Path(tmp) / "finally.db"
    connection._connection = None
    yield
    # Cleanup
    if connection._connection is not None:
        asyncio.get_event_loop().run_until_complete(connection._connection.close())
    connection._connection = None


@pytest_asyncio.fixture
async def db_conn():
    """Initialize the DB and return the connection."""
    db = await connection.init_db()
    yield db


# ---------------------------------------------------------------------------
# Cents helpers
# ---------------------------------------------------------------------------

class TestCentsHelpers:
    """Tests for to_cents, from_cents, and format_dollars."""

    def test_to_cents_basic(self):
        from app.db.cents import to_cents

        assert to_cents(10.00) == 1000
        assert to_cents(0.01) == 1
        assert to_cents(0.00) == 0

    def test_from_cents_basic(self):
        from app.db.cents import from_cents

        assert from_cents(1000) == 10.0
        assert from_cents(1) == 0.01

    @pytest.mark.parametrize("cents", [1, 100, 12345, 999999, 1_000_000])
    def test_round_trip_identity(self, cents):
        """to_cents(from_cents(c)) == c for any integer cent value."""
        from app.db.cents import from_cents, to_cents

        assert to_cents(from_cents(cents)) == cents

    def test_format_dollars(self):
        from app.db.cents import format_dollars

        assert format_dollars(123456) == "$1,234.56"
        assert format_dollars(1000) == "$10.00"
        assert format_dollars(0) == "$0.00"


# ---------------------------------------------------------------------------
# UserRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_returns_default_user_with_cents_converted(db_conn):
    """cash_balance is returned as dollars, raw DB row is cents."""
    from app.db.repositories import UserRepository

    repo = UserRepository()
    user = await repo.get()

    assert user is not None
    assert user["id"] == "default"
    assert user["cash_balance"] == 10000.0  # 1_000_000 cents = $10,000.00

    # Verify raw DB value is cents
    async with db_conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = 'default'"
    ) as cursor:
        row = await cursor.fetchone()
    assert row["cash_balance"] == 1_000_000


@pytest.mark.asyncio
async def test_update_cash_writes_cents(db_conn):
    """update_cash stores the value as cents in the DB."""
    from app.db.repositories import UserRepository

    repo = UserRepository()
    await repo.update_cash(500.55)

    async with db_conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = 'default'"
    ) as cursor:
        row = await cursor.fetchone()
    assert row["cash_balance"] == 50055


@pytest.mark.asyncio
async def test_adjust_cash_returns_new_cents(db_conn):
    """adjust_cash atomically adds delta cents and returns the new balance."""
    from app.db.repositories import UserRepository

    repo = UserRepository()

    # Start at 1_000_000, adjust by -255 cents
    new_cents = await repo.adjust_cash(-255)
    assert new_cents == 999745

    # Verify raw DB
    async with db_conn.execute(
        "SELECT cash_balance FROM users_profile WHERE id = 'default'"
    ) as cursor:
        row = await cursor.fetchone()
    assert row["cash_balance"] == 999745


# ---------------------------------------------------------------------------
# WatchlistRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_all_returns_10_seed_tickers(db_conn):
    """Seed data includes exactly 10 default tickers."""
    from app.db.repositories import WatchlistRepository

    repo = WatchlistRepository()
    entries = await repo.get_all()

    assert len(entries) == 10
    tickers = {e["ticker"] for e in entries}
    assert tickers == {"AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"}


@pytest.mark.asyncio
async def test_add_normalizes_to_uppercase(db_conn):
    """WatchlistRepository.add normalizes ticker to uppercase."""
    from app.db.repositories import WatchlistRepository

    repo = WatchlistRepository()
    result = await repo.add("nflx")

    assert result["ticker"] == "NFLX"


@pytest.mark.asyncio
async def test_add_idempotent(db_conn):
    """Adding the same ticker twice does not create duplicates."""
    from app.db.repositories import WatchlistRepository

    repo = WatchlistRepository()

    await repo.add("nflx")  # idempotent
    entries = await repo.get_all()
    nflx_count = sum(1 for e in entries if e["ticker"] == "NFLX")
    assert nflx_count == 1


@pytest.mark.asyncio
async def test_remove_returns_true_on_success(db_conn):
    """Removing a seeded ticker returns True."""
    from app.db.repositories import WatchlistRepository

    repo = WatchlistRepository()
    result = await repo.remove("AAPL")
    assert result is True


@pytest.mark.asyncio
async def test_remove_returns_false_when_missing(db_conn):
    """Removing a ticker not in the watchlist returns False."""
    from app.db.repositories import WatchlistRepository

    repo = WatchlistRepository()
    result = await repo.remove("ZZZZ")
    assert result is False


# ---------------------------------------------------------------------------
# PositionRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_stores_avg_cost_as_cents(db_conn):
    """upsert stores avg_cost in cents in the DB."""
    from app.db.repositories import PositionRepository

    repo = PositionRepository()
    await repo.upsert("AAPL", quantity=10, avg_cost_dollars=150.25)

    async with db_conn.execute(
        "SELECT avg_cost FROM positions WHERE ticker = 'AAPL'"
    ) as cursor:
        row = await cursor.fetchone()
    assert row["avg_cost"] == 15025


@pytest.mark.asyncio
async def test_get_one_returns_none_when_missing(db_conn):
    """get_one returns None for a ticker with no position."""
    from app.db.repositories import PositionRepository

    repo = PositionRepository()
    result = await repo.get_one("ZZZZ")
    assert result is None


@pytest.mark.asyncio
async def test_delete_returns_true_on_success(db_conn):
    """delete returns True when a position existed and was deleted."""
    from app.db.repositories import PositionRepository

    repo = PositionRepository()
    await repo.upsert("AAPL", quantity=10, avg_cost_dollars=150.0)
    result = await repo.delete("AAPL")
    assert result is True


# ---------------------------------------------------------------------------
# TradeRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insert_stores_price_as_cents(db_conn):
    """insert stores price in cents in the DB."""
    from app.db.repositories import TradeRepository

    repo = TradeRepository()
    row = await repo.insert(ticker="AAPL", side="buy", quantity=10, price_dollars=150.25)

    assert row["price"] == 150.25  # returned as dollars

    async with db_conn.execute(
        "SELECT price FROM trades WHERE ticker = 'AAPL'"
    ) as cursor:
        db_row = await cursor.fetchone()
    assert db_row["price"] == 15025


@pytest.mark.asyncio
async def test_list_recent_orders_desc(db_conn):
    """list_recent returns trades in descending (newest first) order."""
    from app.db.repositories import TradeRepository

    repo = TradeRepository()
    await repo.insert("AAPL", side="buy", quantity=1, price_dollars=100.0)
    await asyncio.sleep(0.001)  # ensure different timestamp
    await repo.insert("GOOGL", side="buy", quantity=1, price_dollars=200.0)

    recent = await repo.list_recent(limit=10)
    assert recent[0]["ticker"] == "GOOGL"
    assert recent[1]["ticker"] == "AAPL"


# ---------------------------------------------------------------------------
# SnapshotRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insert_stores_total_value_as_cents(db_conn):
    """insert stores total_value in cents in the DB."""
    from app.db.repositories import SnapshotRepository

    repo = SnapshotRepository()
    row = await repo.insert(total_value_dollars=10150.25)

    assert row["total_value"] == 10150.25

    async with db_conn.execute(
        "SELECT total_value FROM portfolio_snapshots"
    ) as cursor:
        db_row = await cursor.fetchone()
    assert db_row["total_value"] == 1_015_025


@pytest.mark.asyncio
async def test_list_all_orders_asc(db_conn):
    """list_all returns snapshots in ascending (oldest first) order."""
    from app.db.repositories import SnapshotRepository

    repo = SnapshotRepository()
    await repo.insert(total_value_dollars=10000.0)
    await asyncio.sleep(0.001)
    await repo.insert(total_value_dollars=10500.0)

    all_snapshots = await repo.list_all()
    assert all_snapshots[0]["total_value"] == 10000.0
    assert all_snapshots[1]["total_value"] == 10500.0


# ---------------------------------------------------------------------------
# ChatRepository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insert_with_actions_round_trips_json(db_conn):
    """actions dict is stored as JSON and returned as a dict, not a string."""
    from app.db.repositories import ChatRepository

    repo = ChatRepository()
    actions = {"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10}]}
    row = await repo.insert(role="assistant", content="Done!", actions=actions)

    assert row["actions"] == actions

    # Verify raw DB
    async with db_conn.execute(
        "SELECT actions FROM chat_messages WHERE id = ?", (row["id"],)
    ) as cursor:
        db_row = await cursor.fetchone()
    assert isinstance(db_row["actions"], str)
    assert json.loads(db_row["actions"]) == actions


@pytest.mark.asyncio
async def test_insert_with_no_actions(db_conn):
    """actions=None is stored as NULL and returned as None."""
    from app.db.repositories import ChatRepository

    repo = ChatRepository()
    row = await repo.insert(role="user", content="Hello", actions=None)

    assert row["actions"] is None

    # Verify raw DB
    async with db_conn.execute(
        "SELECT actions FROM chat_messages WHERE id = ?", (row["id"],)
    ) as cursor:
        db_row = await cursor.fetchone()
    assert db_row["actions"] is None
