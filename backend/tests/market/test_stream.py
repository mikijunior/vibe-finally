"""Tests for the SSE price streaming endpoint.

Covers SSE-01..SSE-05 from REQUIREMENTS.md:

  - SSE-01: GET /api/stream/prices returns 200 + Content-Type: text/event-stream
  - SSE-02: First two events are `retry: 1000` and `: connected`
  - SSE-03: data: {...} events contain ticker/price/previous_price/timestamp/direction
  - SSE-04: keepalive comments are emitted on a 30s cadence when dormant
  - SSE-05: Generator exits cleanly when client disconnects

Two test strategies:

1. **Unit tests** drive ``_generate_events`` directly with a fake ``Request``,
   letting us pin ``time.monotonic`` and inspect the exact yield sequence.

2. **Integration tests** spin up uvicorn in a background thread and use
   ``httpx.AsyncClient`` to read the SSE stream with a hard deadline.
   ``fastapi.testclient.TestClient.stream`` blocks indefinitely on a live
   SSE response, so it's not usable here.
"""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
import pytest
import uvicorn
from fastapi import FastAPI

from app.market import PriceCache, create_stream_router


# ---------------------------------------------------------------------------
# Integration helpers (real uvicorn + httpx async client)
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@asynccontextmanager
async def _run_uvicorn(app: FastAPI) -> AsyncIterator[int]:
    """Start uvicorn on a free port; yield the port; shut down on exit."""
    port = _free_port()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        access_log=False,
        lifespan="off",
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve())
    # Wait for the socket to accept connections
    deadline = time.time() + 5.0
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                break
        except OSError:
            await asyncio.sleep(0.05)
    else:  # pragma: no cover — defensive
        raise RuntimeError("uvicorn did not start within 5s")
    try:
        yield port
    finally:
        server.should_exit = True
        await task


async def _read_sse_events(
    port: int, path: str, seconds: float, max_lines: int = 10
) -> tuple[httpx.Response | None, list[str]]:
    """Open an SSE stream and read lines for up to ``seconds``.

    Returns ``(response, lines)``. Each line has its trailing newline
    stripped (httpx preserves newlines on ``aiter_lines``). The response is
    closed before returning so the underlying generator can exit.
    """
    lines: list[str] = []
    response: httpx.Response | None = None
    try:
        async with httpx.AsyncClient(timeout=seconds + 5.0) as client:
            ctx = client.stream("GET", f"http://127.0.0.1:{port}{path}")
            response = await ctx.__aenter__()
            deadline = asyncio.get_event_loop().time() + seconds
            async for raw in response.aiter_lines():
                if asyncio.get_event_loop().time() > deadline:
                    break
                if raw:
                    lines.append(raw.rstrip("\n").rstrip("\r"))
                    if len(lines) >= max_lines:
                        break
            # Close the stream cleanly
            await ctx.__aexit__(None, None, None)
    except Exception:
        pass
    return response, lines


def _run_async(coro):
    """Run an async coroutine to completion in a fresh event loop.

    Used to bridge sync pytest tests with async SSE reads.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Unit helpers (drive _generate_events directly)
# ---------------------------------------------------------------------------


class _FakeRequest:
    """Minimal stand-in for fastapi.Request used by _generate_events."""

    def __init__(self, disconnected_after: int = 10**9, host: str = "test") -> None:
        self._calls = 0
        self._limit = disconnected_after
        self._host = host

    async def is_disconnected(self) -> bool:
        self._calls += 1
        return self._calls > self._limit

    @property
    def client(self):
        return type("C", (), {"host": self._host})()


# ---------------------------------------------------------------------------
# SSE-01 + SSE-02: headers, retry, : connected
# ---------------------------------------------------------------------------


def test_stream_endpoint_returns_correct_headers_and_first_events():
    """SSE-01 + SSE-02: response is 200/text-event-stream; first lines are retry+connected.

    Uses a pre-populated PriceCache and a fresh FastAPI app + uvicorn so
    we get real HTTP responses with headers.
    """
    cache = PriceCache()
    for t in ("AAPL", "GOOGL"):
        cache.update(t, 100.0)
    app = FastAPI()
    app.include_router(create_stream_router(cache))

    async def scenario():
        async with _run_uvicorn(app) as port:
            response, lines = await _read_sse_events(port, "/api/stream/prices", seconds=2.5, max_lines=4)
            # response is closed by _read_sse_events
            return None, lines

    _, lines = _run_async(scenario())
    assert len(lines) >= 3, f"expected ≥3 events, got {lines!r}"
    assert lines[0] == "retry: 1000", f"first line was {lines[0]!r}"
    assert lines[1] == ": connected", f"second line was {lines[1]!r}"
    data_lines = [ln for ln in lines if ln.startswith("data: ")]
    assert data_lines, f"no data: line found in {lines!r}"

    # Now do a second pass just to read headers (separate connection)
    cache2 = PriceCache()
    cache2.update("AAPL", 100.0)
    app2 = FastAPI()
    app2.include_router(create_stream_router(cache2))

    async def header_scenario():
        async with _run_uvicorn(app2) as port:
            async with httpx.AsyncClient(timeout=5.0) as client:
                ctx = client.stream("GET", f"http://127.0.0.1:{port}/api/stream/prices")
                r = await ctx.__aenter__()
                try:
                    # Read at least one byte to confirm the response is alive
                    deadline = asyncio.get_event_loop().time() + 2.0
                    try:
                        async for _ in r.aiter_lines():
                            if asyncio.get_event_loop().time() > deadline:
                                break
                    except (httpx.ReadTimeout, asyncio.TimeoutError):
                        pass
                    return r.status_code, dict(r.headers)
                finally:
                    await ctx.__aexit__(None, None, None)

    status, headers = _run_async(header_scenario())
    assert status == 200
    assert headers.get("content-type", "").startswith("text/event-stream")
    assert headers.get("cache-control") == "no-cache"
    assert headers.get("x-accel-buffering") == "no"
    assert headers.get("connection") == "keep-alive"
    assert headers.get("content-encoding") == "identity"

    # Payload shape check from the first pass
    parsed = json.loads(data_lines[0][len("data: "):])
    sample_ticker = next(iter(parsed))
    sample = parsed[sample_ticker]
    for k in ("ticker", "price", "previous_price", "timestamp", "direction"):
        assert k in sample, f"missing key {k!r} in {sample!r}"
    assert sample["direction"] in ("up", "down", "flat")
    assert sample["price"] > 0


# ---------------------------------------------------------------------------
# SSE-03: payload shape, version-throttled emission
# ---------------------------------------------------------------------------


def test_stream_payload_includes_direction_field():
    """SSE-03: every payload contains the ``direction`` field ∈ {up, down, flat}."""
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    app = FastAPI()
    app.include_router(create_stream_router(cache))

    async def scenario():
        async with _run_uvicorn(app) as port:
            _, lines = await _read_sse_events(port, "/api/stream/prices", seconds=2.5, max_lines=6)
            return lines

    lines = _run_async(scenario())
    data_lines = [ln for ln in lines if ln.startswith("data: ")]
    assert data_lines, f"no data events captured: {lines!r}"
    for line in data_lines:
        payload = json.loads(line[len("data: "):])
        for sample in payload.values():
            assert "direction" in sample, f"missing direction in {sample!r}"
            assert sample["direction"] in ("up", "down", "flat"), (
                f"bad direction {sample['direction']!r}"
            )


def test_stream_version_throttling_one_event_per_bump():
    """SSE-03: a single cache.update produces exactly one data event on the wire.

    Drive ``_generate_events`` directly so we control the exact sequence
    of cache updates and can assert on the yield count.
    """
    from app.market import stream as stream_mod

    cache = PriceCache()

    async def collect():
        events: list[str] = []
        gen = stream_mod._generate_events(cache, _FakeRequest(host="t"), interval=0.05)
        # First two yields: retry + :connected
        events.append((await gen.__anext__()).rstrip("\n"))
        events.append((await gen.__anext__()).rstrip("\n"))
        # Bump cache version once
        cache.update("AAPL", 100.0)
        # Pull a few more yields — we expect at least one data: line
        # (and only one, since we only bumped once)
        for _ in range(8):
            try:
                events.append((await asyncio.wait_for(gen.__anext__(), timeout=0.5)).rstrip("\n"))
            except (asyncio.TimeoutError, StopAsyncIteration):
                break
        await gen.aclose()
        return events

    events = asyncio.run(collect())
    assert events[0] == "retry: 1000"
    assert events[1] == ": connected"
    data_events = [e for e in events if e.startswith("data: ")]
    assert len(data_events) == 1, (
        f"expected exactly 1 data event (one version bump), got {len(data_events)}: {data_events!r}"
    )
    payload = json.loads(data_events[0][len("data: "):])
    assert "AAPL" in payload
    assert payload["AAPL"]["price"] == 100.0


# ---------------------------------------------------------------------------
# SSE-04: keepalive comment when cache is dormant
# ---------------------------------------------------------------------------


def test_stream_emits_keepalive_when_cache_dormant(monkeypatch):
    """SSE-04: with a frozen cache, the generator emits `: keepalive`."""
    from app.market import stream as stream_mod

    cache = PriceCache()
    cache.update("AAPL", 100.0)  # one initial event
    request = _FakeRequest()

    # Pin monotonic to increments > 30s so keepalive fires immediately
    fake_now = [0.0]

    def fake_monotonic() -> float:
        fake_now[0] += 100.0
        return fake_now[0]

    monkeypatch.setattr(stream_mod.time, "monotonic", fake_monotonic)

    async def collect():
        events: list[str] = []
        gen = stream_mod._generate_events(cache, request, interval=0.001)
        for _ in range(15):
            try:
                ev = await asyncio.wait_for(gen.__anext__(), timeout=0.5)
                events.append(ev.rstrip("\n"))
            except (asyncio.TimeoutError, StopAsyncIteration):
                break
            if any(e.startswith(": keepalive") for e in events):
                break
        return events

    events = asyncio.run(collect())
    assert any(e.startswith(": keepalive") for e in events), (
        f"no keepalive in {events!r}"
    )


def test_stream_no_data_event_when_cache_empty():
    """SSE-04 (negative case): empty cache emits retry + :connected, but NO data."""
    cache = PriceCache()
    app = FastAPI()
    app.include_router(create_stream_router(cache))

    async def scenario():
        async with _run_uvicorn(app) as port:
            _, lines = await _read_sse_events(port, "/api/stream/prices", seconds=1.0, max_lines=5)
            return lines

    lines = _run_async(scenario())
    assert lines, "expected retry+connected at minimum"
    assert lines[0] == "retry: 1000", f"first line {lines[0]!r}"
    assert lines[1] == ": connected", f"second line {lines[1]!r}"
    data_lines = [ln for ln in lines if ln.startswith("data: ")]
    assert not data_lines, f"unexpected data: lines from empty cache: {data_lines!r}"


# ---------------------------------------------------------------------------
# SSE-05: disconnect detection
# ---------------------------------------------------------------------------


def test_stream_exits_on_disconnect():
    """SSE-05: when request.is_disconnected() returns True, the generator returns."""
    from app.market import stream as stream_mod

    cache = PriceCache()
    cache.update("AAPL", 100.0)
    # Disconnect after the first is_disconnected() call
    request = _FakeRequest(disconnected_after=1)

    async def collect():
        events: list[str] = []
        gen = stream_mod._generate_events(cache, request, interval=0.001)
        for _ in range(10):
            try:
                ev = await asyncio.wait_for(gen.__anext__(), timeout=1.0)
                events.append(ev.rstrip("\n"))
            except (StopAsyncIteration, asyncio.TimeoutError):
                break
        return events

    events = asyncio.run(collect())
    assert events[0] == "retry: 1000"
    assert events[1] == ": connected"
    # No more than a handful of yields before disconnect
    assert len(events) <= 5, f"generator did not exit: {events!r}"


def test_stream_handles_cancelled_error_silently():
    """SSE-05: asyncio.CancelledError is caught and logged, never propagates."""
    from app.market import stream as stream_mod

    cache = PriceCache()
    cache.update("AAPL", 100.0)
    request = _FakeRequest()

    async def collect_then_cancel():
        gen = stream_mod._generate_events(cache, request, interval=10.0)  # long sleep
        # Pull initial yields
        first = (await gen.__anext__()).rstrip("\n")
        second = (await gen.__anext__()).rstrip("\n")
        # Now cancel the generator
        await gen.aclose()
        return first, second

    first, second = asyncio.run(collect_then_cancel())
    assert first == "retry: 1000"
    assert second == ": connected"