"""Shared pytest fixtures for the FinAlly backend test suite.

The fixtures in this module are designed to be composed:

- ``fresh_db``       — point the SQLite connection at a temp DB and reset state
- ``testing_env``    — set ``TESTING=1`` and reload ``app.main`` so test
                       endpoints (``/cache/state``, ``/watchlist/test-add/...``)
                       are registered
- ``client``         — a ``TestClient(app)`` that runs lifespan startup/shutdown
- ``seeded_client``  — like ``client`` but waits up to 2s for the simulator to
                       populate ``len(price_cache) >= 10`` so trade tests have
                       live prices to work with
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest

import app.db.connection as connection


def _cleanup_state() -> None:
    """Reset module-level singletons after a test."""
    import app.main as main

    main.state.price_cache = None
    main.state.market_source = None
    connection._connection = None


@pytest.fixture
def fresh_db():
    """Point SQLite at an isolated temp DB and reset module state."""
    tmp = tempfile.mkdtemp()
    connection.DB_PATH = Path(tmp) / "finally.db"
    connection._connection = None
    _cleanup_state()
    yield
    _cleanup_state()


@pytest.fixture
def testing_env(fresh_db, monkeypatch):
    """Set ``TESTING=1`` and reload ``app.main`` so test endpoints are registered."""
    monkeypatch.setenv("TESTING", "1")
    from importlib import reload

    import app.main

    reload(app.main)
    yield
    monkeypatch.delenv("TESTING", raising=False)


@pytest.fixture
def client(testing_env):
    """HTTP client with lifespan startup and shutdown fired by ``with`` context.

    Yields a ``fastapi.testclient.TestClient`` already inside its context
    manager so handlers see the live ``PriceCache`` and ``MarketDataSource``.
    """
    from fastapi.testclient import TestClient

    import app.main as main

    with TestClient(main.app) as c:
        yield c


@pytest.fixture
async def seeded_client(client):
    """Like ``client`` but waits for ``len(price_cache) >= 10`` before yielding.

    Trade tests need live prices; without this wait, ``price_cache.get_price``
    returns ``None`` and trades return 400. Removes any tickers the test
    scenario may have added (default seed tickers remain).
    """
    import app.main as main

    for _ in range(40):  # 40 * 50ms = 2s max
        await asyncio.sleep(0.05)
        cache = main.state.price_cache
        if cache is not None and len(cache) >= 10:
            break
    yield client
    # Best-effort cleanup of any tickers beyond the default 10
    cache = main.state.price_cache
    if cache is None:
        return
    for ticker in list(cache.get_all().keys()):
        if ticker not in {
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
            "NVDA", "META", "JPM", "V", "NFLX",
        }:
            cache.remove(ticker)
