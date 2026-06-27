"""SSE streaming endpoint for live price updates."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .cache import PriceCache

logger = logging.getLogger(__name__)

# Module-level singleton router for ``app.main``. Each ``create_stream_router``
# call creates its OWN ``APIRouter`` so tests that construct an isolated
# FastAPI app + fresh PriceCache aren't affected by routes registered earlier.
router = APIRouter(prefix="/api/stream", tags=["streaming"])

# Inner polling cadence — how often we check the cache for a new version.
_CADENCE_S = 0.5

# Keepalive cadence — emit an SSE comment every 30s even when prices are dormant,
# so proxies (nginx, Cloudflare, App Runner) don't drop the idle connection.
_KEEPALIVE_INTERVAL_S = 30.0


def _resolve_cache(price_cache: PriceCache | callable) -> PriceCache:
    """Return the live PriceCache, accepting either an instance or a zero-arg callable.

    The factory accepts both forms because ``app.main`` wires it with a callable
    (resolved at request time, after the lifespan has populated the cache) and
    tests / docs wire it with a direct ``PriceCache()`` instance. Either way,
    by the time SSE events are yielded, the cache must be non-None.
    """
    if callable(price_cache):
        cache = price_cache()
    else:
        cache = price_cache
    if cache is None:
        raise RuntimeError("PriceCache not yet initialized")
    return cache


def create_stream_router(price_cache: PriceCache | callable) -> APIRouter:
    """Create the SSE streaming router with a reference to the price cache.

    This factory pattern lets us inject the PriceCache without globals.

    The ``price_cache`` argument may be either a ``PriceCache`` instance or a
    zero-arg callable returning one — see ``_resolve_cache`` for details.

    Each call returns a fresh ``APIRouter`` so tests with isolated
    ``PriceCache`` instances aren't tied to the module-level singleton
    registered by ``app.main``.
    """
    local_router = APIRouter(prefix="/api/stream", tags=["streaming"])

    @local_router.get("/prices")
    async def stream_prices(request: Request) -> StreamingResponse:
        """SSE endpoint for live price updates.

        Streams all tracked ticker prices every ~500ms when the PriceCache
        version changes. The client connects with EventSource and receives
        events in the format:

            data: {"AAPL": {"ticker": "AAPL", "price": 190.50, ...}, ...}

        Includes a retry directive so the browser auto-reconnects on
        disconnection (EventSource built-in behavior), and a 30s keepalive
        comment so long-lived idle connections survive reverse proxies.
        """
        return StreamingResponse(
            _generate_events(price_cache, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering if proxied
                # Defensive: some proxies default to gzip and break SSE framing.
                "Content-Encoding": "identity",
            },
        )

    return local_router


async def _generate_events(
    price_cache: PriceCache | callable,
    request: Request,
    interval: float = _CADENCE_S,
) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted price events.

    Emits:
      - `retry: 1000` on connect so EventSource auto-reconnects after 1s.
      - `: connected` comment so the client sees activity immediately.
      - `data: {...}` event whenever `price_cache.version` changes
        (one event per version bump; no thrash when prices are stable).
      - `: keepalive` comment every 30s when no price event has been emitted,
        so reverse proxies don't drop the connection.

    Stops cleanly when:
      - `await request.is_disconnected()` returns True (graceful disconnect).
      - The asyncio task is cancelled (uvicorn disconnects); CancelledError
        is caught and logged so it never bubbles as an error.
    """
    # Resolve the live cache (handles both instance and callable forms)
    cache = _resolve_cache(price_cache)

    # Tell the client to retry after 1 second if the connection drops
    yield "retry: 1000\n\n"
    # Immediately emit a comment so the client sees activity right away
    yield ": connected\n\n"

    last_version = -1
    last_keepalive = time.monotonic()
    client_ip = request.client.host if request.client else "unknown"
    logger.info("SSE client connected: %s", client_ip)

    try:
        while True:
            # Check for client disconnect (SSE-05)
            if await request.is_disconnected():
                logger.info("SSE client disconnected: %s", client_ip)
                break

            current_version = cache.version
            if current_version != last_version:
                last_version = current_version
                prices = cache.get_all()

                if prices:
                    data = {ticker: update.to_dict() for ticker, update in prices.items()}
                    payload = json.dumps(data)
                    yield f"data: {payload}\n\n"
                    # Reset keepalive timer when we just sent real data
                    last_keepalive = time.monotonic()

            now = time.monotonic()
            if now - last_keepalive >= _KEEPALIVE_INTERVAL_S:
                # SSE-04: proxy-busting comment, no payload
                yield ": keepalive\n\n"
                last_keepalive = now

            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        logger.info("SSE stream cancelled for: %s", client_ip)
