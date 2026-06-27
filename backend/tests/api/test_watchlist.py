"""Tests for the ``/api/watchlist`` endpoints (GET, POST, DELETE)."""

from __future__ import annotations

import pytest

DEFAULT_TICKERS = {
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA",
    "NVDA", "META", "JPM", "V", "NFLX",
}


@pytest.mark.asyncio
async def test_watchlist_lists_default_tickers(client):
    """GET /api/watchlist returns 200 with the 10 default tickers."""
    response = client.get("/api/watchlist")
    assert response.status_code == 200
    data = response.json()
    entries = data["entries"]
    assert len(entries) == 10, f"expected 10 entries, got {len(entries)}"
    tickers = {e["ticker"] for e in entries}
    assert tickers == DEFAULT_TICKERS


@pytest.mark.asyncio
async def test_watchlist_add_new_ticker(seeded_client):
    """POST /api/watchlist adds a new ticker and the cache picks up the seed price."""
    response = seeded_client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "added"
    assert body["already_present"] is False
    assert body["ticker"] == "PYPL"

    # Verify it's now listed with a positive price (simulator seed)
    listing = seeded_client.get("/api/watchlist").json()
    pypl = next((e for e in listing["entries"] if e["ticker"] == "PYPL"), None)
    assert pypl is not None
    assert pypl["price"] > 0


@pytest.mark.asyncio
async def test_watchlist_add_is_idempotent(seeded_client):
    """POST /api/watchlist twice with the same ticker is idempotent."""
    first = seeded_client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert first.status_code == 200
    assert first.json()["already_present"] is False

    second = seeded_client.post("/api/watchlist", json={"ticker": "PYPL"})
    assert second.status_code == 200
    assert second.json()["already_present"] is True

    listing = seeded_client.get("/api/watchlist").json()
    pypl_rows = [e for e in listing["entries"] if e["ticker"] == "PYPL"]
    assert len(pypl_rows) == 1, f"expected exactly one PYPL row, got {len(pypl_rows)}"


@pytest.mark.asyncio
async def test_watchlist_add_rejects_invalid_format(client):
    """POST /api/watchlist rejects empty / non-letter tickers with 422."""
    empty = client.post("/api/watchlist", json={"ticker": ""})
    assert empty.status_code == 422

    digits = client.post("/api/watchlist", json={"ticker": "123"})
    assert digits.status_code == 422

    with_dash = client.post("/api/watchlist", json={"ticker": "AA-PL"})
    assert with_dash.status_code == 422


@pytest.mark.asyncio
async def test_watchlist_remove_returns_404_when_missing(client):
    """DELETE /api/watchlist/{ticker} returns 404 for an unknown ticker."""
    response = client.delete("/api/watchlist/ZZZZ")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_watchlist_remove_drops_ticker_and_price(seeded_client):
    """POST then DELETE removes the ticker from listing and PriceCache."""
    seeded_client.post("/api/watchlist", json={"ticker": "PYPL"})

    # Verify present
    before = seeded_client.get("/api/watchlist").json()
    assert any(e["ticker"] == "PYPL" for e in before["entries"])

    response = seeded_client.delete("/api/watchlist/PYPL")
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "removed"
    assert body["ticker"] == "PYPL"

    # Verify removed from listing
    after = seeded_client.get("/api/watchlist").json()
    assert not any(e["ticker"] == "PYPL" for e in after["entries"])

    # Verify removed from PriceCache
    import app.main as main

    assert main.state.price_cache.get("PYPL") is None


@pytest.mark.asyncio
async def test_watchlist_add_uppercases_lowercase_ticker(client):
    """POST normalizes lowercase ticker to uppercase before storing."""
    response = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert response.status_code == 200
    assert response.json()["ticker"] == "PYPL"


@pytest.mark.asyncio
async def test_watchlist_listing_includes_added_at_and_price(client):
    """Each watchlist entry exposes ticker, added_at, and price fields."""
    response = client.get("/api/watchlist")
    assert response.status_code == 200
    for entry in response.json()["entries"]:
        assert "ticker" in entry
        assert "added_at" in entry
        assert "price" in entry
        assert isinstance(entry["price"], (int, float))
