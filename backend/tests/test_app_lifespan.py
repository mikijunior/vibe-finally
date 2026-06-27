"""Tests for FastAPI app lifespan: startup, cache/source sync, and shutdown."""

from __future__ import annotations

import asyncio
import tempfile

import pytest

# Patch DB_PATH before importing app
import app.db.connection as connection


def cleanup_state():
    """Reset all global state after a test."""
    import app.main as main

    main.state.price_cache = None
    main.state.market_source = None
    connection._connection = None


@pytest.fixture
def fresh_db():
    """Set up isolated temp DB for this test."""
    tmp = tempfile.mkdtemp()
    connection.DB_PATH = __import__("pathlib").Path(tmp) / "finally.db"
    connection._connection = None
    cleanup_state()
    yield
    cleanup_state()


@pytest.fixture
def testing_env(fresh_db, monkeypatch):
    """Set TESTING=1 so test endpoints are registered."""
    monkeypatch.setenv("TESTING", "1")
    # Force re-import to pick up env var
    from importlib import reload

    import app.main

    reload(app.main)
    yield
    # Cleanup
    monkeypatch.delenv("TESTING", raising=False)


@pytest.fixture
def client(testing_env):
    """HTTP client with lifespan management.

    Entering this fixture runs lifespan startup (init_db, PriceCache,
    MarketDataSource.start). Exiting runs lifespan shutdown
    (market_source.stop, close_db).
    """
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        yield client


def test_lifespan_starts_market_source_for_default_tickers(client):
    """MarketDataSource starts with 10 default tickers on app startup."""
    import app.main as main

    # Verify 10 default tickers are in the market source
    tickers = main.state.market_source.get_tickers()
    assert len(tickers) == 10, f"Expected 10 tickers, got {len(tickers)}: {tickers}"
    assert set(tickers) == {
        "AAPL",
        "GOOGL",
        "MSFT",
        "AMZN",
        "TSLA",
        "NVDA",
        "META",
        "JPM",
        "V",
        "NFLX",
    }


def test_lifespan_prices_flow_into_cache(client):
    """Price updates from simulator flow into PriceCache."""
    import app.main as main

    # Wait briefly for at least one price update
    async def wait_for_price():
        for _ in range(20):  # 20 * 50ms = 1s max
            await asyncio.sleep(0.05)
            if main.state.price_cache and main.state.price_cache.version > 0:
                return True
        return False

    result = asyncio.run(wait_for_price())
    assert result, "PriceCache version never incremented"

    # Verify prices are non-zero
    prices = main.state.price_cache.get_all()
    assert len(prices) == 10, f"Expected 10 prices, got {len(prices)}"
    for ticker, update in prices.items():
        assert update.price > 0, f"{ticker} has price {update.price}, expected > 0"


def test_watchlist_add_propagates_to_cache_and_source(client):
    """WatchlistRepository.add('PYPL') syncs to MarketDataSource and PriceCache."""
    import app.main as main

    # Add PYPL to the watchlist via test endpoint
    response = client.post("/watchlist/test-add/PYPL")
    assert response.status_code == 200
    data = response.json()
    assert data["added"]["ticker"] == "PYPL"

    # Verify market source is tracking PYPL
    tickers = main.state.market_source.get_tickers()
    assert "PYPL" in tickers, f"PYPL not in market source tickers: {tickers}"

    # Verify PriceCache has a price for PYPL
    price = main.state.price_cache.get("PYPL")
    assert price is not None, "PYPL not found in PriceCache"
    assert price.price > 0, f"PYPL has invalid price: {price.price}"


def test_watchlist_remove_propagates_from_cache_and_source(client):
    """WatchlistRepository.remove('AAPL') drops it from MarketDataSource and PriceCache."""
    import app.main as main

    # Remove AAPL via test endpoint
    response = client.post("/watchlist/test-remove/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["removed"] is True
    assert data["ticker"] == "AAPL"

    # Verify market source no longer tracks AAPL
    tickers = main.state.market_source.get_tickers()
    assert "AAPL" not in tickers, f"AAPL still in market source: {tickers}"

    # Verify PriceCache no longer has AAPL
    price = main.state.price_cache.get("AAPL")
    assert price is None, f"AAPL still in PriceCache: {price}"


def test_lifespan_shutdown_stops_source_and_closes_db(fresh_db, testing_env, monkeypatch):
    """Exiting TestClient context manager stops source and closes DB.

    This test creates its own client context to control the shutdown timing.
    We capture pre-shutdown state, exit the context, then verify cleanup.
    """
    from fastapi.testclient import TestClient

    import app.main as main

    # Import app AFTER fresh_db sets temp DB_PATH
    from app.main import app

    # Create client inside this test so we control shutdown
    # (TestClient's __exit__ triggers lifespan shutdown — assignment unused by design)
    with TestClient(app):
        # Pre-shutdown: verify everything is initialized
        assert main.state.market_source is not None
        assert main.state.price_cache is not None
        assert connection._connection is not None

        # Exit context manager → triggers lifespan shutdown
    # After __exit__: lifespan shutdown should have run
    assert main.state.market_source is None, "market_source not cleared on shutdown"
    assert main.state.price_cache is None, "price_cache not cleared on shutdown"
    assert connection._connection is None, "DB connection not closed on shutdown"


def test_health_endpoint_returns_ok(client):
    """GET /health returns 200 with status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
