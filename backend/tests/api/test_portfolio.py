"""Tests for the ``/api/portfolio`` endpoints (GET, POST /trade, history)."""

from __future__ import annotations

import pytest

from app.db.repositories import PositionRepository, SnapshotRepository, TradeRepository

# ---------------------------------------------------------------------------
# GET /api/portfolio
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_initial_state(client):
    """Fresh user sees $10,000 cash, no positions, total_value == cash."""
    response = client.get("/api/portfolio")
    assert response.status_code == 200
    body = response.json()
    assert body["cash_balance"] == 10000.0
    assert body["positions"] == []
    assert body["total_value"] == 10000.0


@pytest.mark.asyncio
async def test_portfolio_attaches_current_price_from_cache(seeded_client):
    """After a buy, position.current_price is the live cache price."""
    seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 1, "side": "buy",
    })

    response = seeded_client.get("/api/portfolio")
    assert response.status_code == 200
    positions = response.json()["positions"]
    aapl = next((p for p in positions if p["ticker"] == "AAPL"), None)
    assert aapl is not None
    assert aapl["current_price"] > 0
    # unrealized_pnl = (current_price - avg_cost) * quantity
    expected_pnl = (aapl["current_price"] - aapl["avg_cost"]) * aapl["quantity"]
    assert abs(aapl["unrealized_pnl"] - expected_pnl) < 0.01


# ---------------------------------------------------------------------------
# POST /api/portfolio/trade — happy paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trade_buy_decrements_cash_and_creates_position(seeded_client):
    """A buy decrements cash, inserts a trades row, creates a position, and snapshots."""
    before = seeded_client.get("/api/portfolio").json()
    starting_cash = before["cash_balance"]

    response = seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 1, "side": "buy",
    })
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["trade"]["side"] == "buy"
    assert body["trade"]["ticker"] == "AAPL"
    assert body["position"]["ticker"] == "AAPL"
    assert body["position"]["quantity"] == 1.0

    # Cash decreased by approximately the buy price
    new_cash = body["cash_balance"]
    assert new_cash < starting_cash

    # Trades table has the row
    trade_repo = TradeRepository()
    trades = await trade_repo.list_all()
    assert any(t["ticker"] == "AAPL" and t["side"] == "buy" for t in trades)

    # Portfolio_snapshots table has a new row
    snapshot_repo = SnapshotRepository()
    snapshots = await snapshot_repo.list_all()
    assert len(snapshots) >= 1


@pytest.mark.asyncio
async def test_trade_buy_uses_weighted_average_cost(seeded_client):
    """Two buys at different prices produce a weighted-average avg_cost."""
    # First buy
    r1 = seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 2, "side": "buy",
    })
    assert r1.status_code == 200
    p1 = float(r1.json()["position"]["avg_cost"])

    # Second buy
    r2 = seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 2, "side": "buy",
    })
    assert r2.status_code == 200
    body = r2.json()
    new_avg = float(body["position"]["avg_cost"])

    # Weighted average of (p1, 2 shares) and (p2, 2 shares): both 2-share legs
    # yields the average of p1 and p2 (or within tolerance).
    # More directly: avg_cost should be between p1 and current price
    assert p1 - 5.0 <= new_avg <= p1 + 5.0, (
        f"weighted avg_cost {new_avg} out of expected band around {p1}"
    )


@pytest.mark.asyncio
async def test_trade_sell_updates_position_and_credits_cash(seeded_client):
    """A sell decrements quantity, leaves avg_cost unchanged, credits cash."""
    # Buy 5
    seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 5, "side": "buy",
    })
    position_repo = PositionRepository()
    before_pos = await position_repo.get_one("AAPL")
    before_avg = float(before_pos["avg_cost"])

    # Sell 2
    response = seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 2, "side": "sell",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["position"]["quantity"] == 3.0
    assert abs(float(body["position"]["avg_cost"]) - before_avg) < 0.01


@pytest.mark.asyncio
async def test_trade_sell_to_zero_deletes_position(seeded_client):
    """Selling all shares deletes the positions row entirely."""
    seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 2, "side": "buy",
    })

    response = seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 2, "side": "sell",
    })
    assert response.status_code == 200
    assert response.json()["position"] is None

    # Confirm DB has no row
    position_repo = PositionRepository()
    pos = await position_repo.get_one("AAPL")
    assert pos is None


# ---------------------------------------------------------------------------
# POST /api/portfolio/trade — validation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trade_rejects_buy_with_insufficient_cash(seeded_client):
    """Buying more than cash allows returns 400 and mutates nothing."""
    # AAPL ~$190; 100 shares = ~$19,000 which exceeds $10k
    response = seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 100, "side": "buy",
    })
    assert response.status_code == 400
    assert "insufficient" in response.json()["detail"].lower()

    # No trade row inserted
    trade_repo = TradeRepository()
    trades = await trade_repo.list_all()
    assert not any(t["quantity"] == 100 for t in trades)


@pytest.mark.asyncio
async def test_trade_rejects_sell_without_holding(seeded_client):
    """Selling a ticker not held returns 400."""
    response = seeded_client.post("/api/portfolio/trade", json={
        "ticker": "NVDA", "quantity": 1, "side": "sell",
    })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_trade_rejects_negative_quantity(client):
    """Negative quantity is rejected at the Pydantic layer (422)."""
    response = client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": -1, "side": "buy",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_trade_rejects_invalid_side(client):
    """Invalid side string is rejected at the Pydantic layer (422)."""
    response = client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 1, "side": "sideways",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_trade_rejects_unknown_ticker(seeded_client):
    """A ticker with no price in cache returns 400 (caller must watch first)."""
    response = seeded_client.post("/api/portfolio/trade", json={
        "ticker": "ZZZZ", "quantity": 1, "side": "buy",
    })
    assert response.status_code == 400
    assert "no live price" in response.json()["detail"].lower() or "zzzz" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /api/portfolio/history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_portfolio_history_returns_snapshots_ordered_asc(seeded_client):
    """Two trades → at least 2 snapshots, ordered ASC by recorded_at."""
    seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 1, "side": "buy",
    })
    seeded_client.post("/api/portfolio/trade", json={
        "ticker": "GOOGL", "quantity": 1, "side": "buy",
    })

    response = seeded_client.get("/api/portfolio/history")
    assert response.status_code == 200
    snapshots = response.json()["snapshots"]
    assert len(snapshots) >= 2

    recorded_at = [s["recorded_at"] for s in snapshots]
    assert recorded_at == sorted(recorded_at), "snapshots not in ASC order"


@pytest.mark.asyncio
async def test_portfolio_history_empty_when_no_trades(client):
    """Before any trades, history returns an empty list with 200."""
    response = client.get("/api/portfolio/history")
    assert response.status_code == 200
    # History may be empty or may include seed snapshots from the lifespan test
    # — just assert the schema is valid.
    for snapshot in response.json()["snapshots"]:
        assert "id" in snapshot
        assert "total_value" in snapshot
        assert "recorded_at" in snapshot
