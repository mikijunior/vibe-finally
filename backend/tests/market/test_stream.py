"""Tests for SSE market data streaming."""

import json
from types import SimpleNamespace

import pytest
from fastapi.routing import APIRoute

from app.market.cache import PriceCache
from app.market.stream import _generate_events, create_stream_router


class DisconnectAfterFirstPayloadRequest:
    """Minimal request double that disconnects after the first data payload."""

    def __init__(self) -> None:
        self.client = SimpleNamespace(host="testclient")
        self.calls = 0

    async def is_disconnected(self) -> bool:
        self.calls += 1
        return self.calls > 1


@pytest.mark.asyncio
async def test_generate_events_sends_retry_then_price_payload():
    cache = PriceCache()
    cache.update("AAPL", 190.50, timestamp=1234567890.0)
    request = DisconnectAfterFirstPayloadRequest()
    events = _generate_events(cache, request, interval=0)

    retry = await anext(events)
    payload = await anext(events)
    await events.aclose()

    assert retry == "retry: 1000\n\n"
    assert payload.startswith("data: ")
    data = json.loads(payload.removeprefix("data: ").strip())
    assert data["AAPL"]["price"] == 190.50
    assert data["AAPL"]["direction"] == "flat"


def test_create_stream_router_returns_fresh_router_each_call():
    cache = PriceCache()

    router_one = create_stream_router(cache)
    router_two = create_stream_router(cache)

    assert router_one is not router_two
    assert len([route for route in router_one.routes if isinstance(route, APIRoute)]) == 1
    assert len([route for route in router_two.routes if isinstance(route, APIRoute)]) == 1
