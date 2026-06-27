"""Tests for the MockLLMClient keyword-routed responses."""

from __future__ import annotations

import pytest

from app.llm import ChatResponse, MockLLMClient


@pytest.mark.asyncio
async def test_mock_buy_keyword():
    """``buy 10 AAPL`` produces a single buy trade of 10 shares of AAPL."""
    client = MockLLMClient()
    response = await client.complete_structured(
        [{"role": "user", "content": "buy 10 AAPL"}],
        ChatResponse,
    )
    assert isinstance(response, ChatResponse)
    assert len(response.trades) == 1
    assert response.trades[0].ticker == "AAPL"
    assert response.trades[0].side == "buy"
    assert response.trades[0].quantity == 10.0
    assert response.watchlist_changes == []


@pytest.mark.asyncio
async def test_mock_sell_keyword():
    """``sell 5 NVDA`` produces a single sell trade of 5 shares of NVDA."""
    client = MockLLMClient()
    response = await client.complete_structured(
        [{"role": "user", "content": "sell 5 NVDA"}],
        ChatResponse,
    )
    assert len(response.trades) == 1
    assert response.trades[0].ticker == "NVDA"
    assert response.trades[0].side == "sell"
    assert response.trades[0].quantity == 5.0


@pytest.mark.asyncio
async def test_mock_watchlist_add_keyword():
    """``add PYPL`` produces a watchlist add action."""
    client = MockLLMClient()
    response = await client.complete_structured(
        [{"role": "user", "content": "add PYPL"}],
        ChatResponse,
    )
    assert response.trades == []
    assert len(response.watchlist_changes) == 1
    assert response.watchlist_changes[0].ticker == "PYPL"
    assert response.watchlist_changes[0].action == "add"


@pytest.mark.asyncio
async def test_mock_watchlist_remove_keyword():
    """``remove NFLX`` produces a watchlist remove action."""
    client = MockLLMClient()
    response = await client.complete_structured(
        [{"role": "user", "content": "remove NFLX"}],
        ChatResponse,
    )
    assert response.trades == []
    assert len(response.watchlist_changes) == 1
    assert response.watchlist_changes[0].ticker == "NFLX"
    assert response.watchlist_changes[0].action == "remove"


@pytest.mark.asyncio
async def test_mock_default_response():
    """A message with no recognized keyword returns a default summary."""
    client = MockLLMClient()
    response = await client.complete_structured(
        [{"role": "user", "content": "what is my portfolio?"}],
        ChatResponse,
    )
    assert response.trades == []
    assert response.watchlist_changes == []
    assert "Mock portfolio summary" in response.message


@pytest.mark.asyncio
async def test_mock_handles_lowercase_ticker():
    """``buy 3 msft`` uppercases the ticker to MSFT."""
    client = MockLLMClient()
    response = await client.complete_structured(
        [{"role": "user", "content": "buy 3 msft"}],
        ChatResponse,
    )
    assert response.trades[0].ticker == "MSFT"
    assert response.trades[0].quantity == 3.0


@pytest.mark.asyncio
async def test_mock_no_user_message():
    """Empty messages list returns a default mock response."""
    client = MockLLMClient()
    response = await client.complete_structured([], ChatResponse)
    assert response.message == "Mock: no user message found"
    assert response.trades == []
    assert response.watchlist_changes == []


@pytest.mark.asyncio
async def test_mock_parses_fractional_quantity():
    """``buy 10.5 shares of AAPL`` parses quantity as float."""
    client = MockLLMClient()
    response = await client.complete_structured(
        [{"role": "user", "content": "buy 10.5 shares of AAPL"}],
        ChatResponse,
    )
    assert len(response.trades) == 1
    assert response.trades[0].ticker == "AAPL"
    assert response.trades[0].quantity == 10.5