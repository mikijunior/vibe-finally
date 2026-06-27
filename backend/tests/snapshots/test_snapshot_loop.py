"""Tests for the snapshot loop (SNAP-01) and trade-time snapshots (SNAP-02).

Covers:

- ``_compute_total_value`` math against a real PriceCache + SQLite stack
- Loop cadence: rows accumulate at the configured interval
- Shutdown: stop_event + task.cancel terminate the loop within 1 second
- Error resilience: a single failed insert does not kill the loop
- Missing prices: positions for tickers absent from the cache contribute 0
- Trade-time snapshot: POST /api/portfolio/trade inserts exactly one row
- Lifespan wiring: app.state.snapshot_task is created on startup and cleared on shutdown
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest

from app.db.cents import from_cents
from app.db.connection import get_db
from app.db.repositories import SnapshotRepository
from app.snapshots import _compute_total_value, start_snapshot_loop

# ---------------------------------------------------------------------------
# _compute_total_value math
# ---------------------------------------------------------------------------


async def test_compute_total_value_with_only_cash(seeded_client):
    """With no positions, total value equals the seeded $10,000 cash."""
    import app.main as main

    val = await _compute_total_value(main.state.price_cache)
    assert val == pytest.approx(10000.0, abs=0.01)


async def test_compute_total_value_includes_position_value(seeded_client):
    """After buying 1 AAPL, total = cash_after_buy + 1 * live_price."""
    import app.main as main

    trade_resp = seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 1, "side": "buy",
    })
    assert trade_resp.status_code == 200, trade_resp.text
    body = trade_resp.json()
    cash_after = float(body["cash_balance"])

    aapl_price = main.state.price_cache.get_price("AAPL")
    assert aapl_price is not None and aapl_price > 0

    total = await _compute_total_value(main.state.price_cache)
    assert total == pytest.approx(cash_after + aapl_price, abs=0.05)


# ---------------------------------------------------------------------------
# Loop cadence
# ---------------------------------------------------------------------------


async def test_snapshot_loop_writes_rows_on_cadence(seeded_client):
    """A loop with 0.5s interval writes at least 3 rows in 1.7 seconds."""
    import app.main as main

    # Stop the default 30s loop the lifespan started.
    if main.state.snapshot_task is not None and not main.state.snapshot_task.done():
        if main.state._snapshot_stop is not None:
            main.state._snapshot_stop.set()
        main.state.snapshot_task.cancel()
        try:
            await main.state.snapshot_task
        except (asyncio.CancelledError, Exception):
            pass

    db = await get_db()
    before_cur = await db.execute(
        "SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id='default'"
    )
    before_row = await before_cur.fetchone()
    before = before_row[0]

    stop = asyncio.Event()
    task = start_snapshot_loop(main.state.price_cache, stop, interval_seconds=0.5)
    try:
        await asyncio.sleep(1.7)
    finally:
        stop.set()
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            task.cancel()

    after_cur = await db.execute(
        "SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id='default'"
    )
    after_row = await after_cur.fetchone()
    after = after_row[0]

    assert after - before >= 3, f"expected >=3 new snapshots, got {after - before}"


async def test_snapshot_loop_respects_stop_event(seeded_client):
    """Setting stop_event stops further inserts; the DB row count stops growing."""
    import app.main as main

    # Use the stop event the lifespan created. We can't await its task here
    # because the lifespan's task is bound to TestClient's internal loop,
    # not pytest-asyncio's test loop — but stop_event.set() is just a flag
    # and is safe to call from any loop.
    assert main.state._snapshot_stop is not None
    main.state._snapshot_stop.set()

    db = await get_db()
    cur = await db.execute(
        "SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id='default'"
    )
    count_at_stop = (await cur.fetchone())[0]

    # No new rows should be inserted after the stop event is set.
    await asyncio.sleep(1.0)
    cur2 = await db.execute(
        "SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id='default'"
    )
    count_after_sleep = (await cur2.fetchone())[0]
    assert count_after_sleep == count_at_stop


async def test_snapshot_loop_survives_insert_failure(seeded_client, monkeypatch):
    """A failed insert iteration is logged and the loop continues on the next tick."""
    import app.main as main

    call_count = {"n": 0}
    original_insert = SnapshotRepository.insert

    async def flaky_insert(self, total_value_dollars: float):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("boom")
        return await original_insert(self, total_value_dollars)

    monkeypatch.setattr(SnapshotRepository, "insert", flaky_insert)

    # Stop the default loop so it doesn't pollute the count.
    if main.state.snapshot_task is not None and not main.state.snapshot_task.done():
        if main.state._snapshot_stop is not None:
            main.state._snapshot_stop.set()
        main.state.snapshot_task.cancel()
        try:
            await main.state.snapshot_task
        except (asyncio.CancelledError, Exception):
            pass

    db = await get_db()
    before_cur = await db.execute(
        "SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id='default'"
    )
    before = (await before_cur.fetchone())[0]

    stop = asyncio.Event()
    task = start_snapshot_loop(main.state.price_cache, stop, interval_seconds=0.3)
    try:
        await asyncio.sleep(1.5)
    finally:
        stop.set()
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            task.cancel()

    # Loop survived at least one failed iteration (task shouldn't be in a broken state).
    # The patched insert was called multiple times.
    assert call_count["n"] >= 2

    # And at least one row landed AFTER the patched call failed.
    after_cur = await db.execute(
        "SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id='default'"
    )
    after = (await after_cur.fetchone())[0]
    assert after > before, "loop recovered but never wrote a successful insert"


async def test_snapshot_loop_uses_zero_for_missing_prices(seeded_client):
    """A position for a ticker absent from PriceCache contributes 0 to total."""
    import app.main as main

    db = await get_db()
    now = datetime.now(timezone.utc).isoformat()
    # Insert a position for a ticker the cache does NOT know about.
    await db.execute(
        "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
        "VALUES (?, 'default', ?, ?, ?, ?)",
        (str(uuid.uuid4()), "ZZZZ", 5.0, 12345, now),
    )
    await db.commit()

    # Sanity: ZZZZ is not in cache.
    assert main.state.price_cache.get_price("ZZZZ") is None

    total = await _compute_total_value(main.state.price_cache)
    # total = cash + (5 * 0 for missing ZZZZ) = 10000
    assert total == pytest.approx(10000.0, abs=0.01)


# ---------------------------------------------------------------------------
# Trade-time snapshot (SNAP-02)
# ---------------------------------------------------------------------------


async def test_trade_records_inline_snapshot(seeded_client):
    """A successful trade inserts exactly one snapshot row (SNAP-02)."""
    db = await get_db()
    before_cur = await db.execute(
        "SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id='default'"
    )
    before = (await before_cur.fetchone())[0]

    trade_resp = seeded_client.post("/api/portfolio/trade", json={
        "ticker": "AAPL", "quantity": 1, "side": "buy",
    })
    assert trade_resp.status_code == 200, trade_resp.text
    body = trade_resp.json()
    cash_after = float(body["cash_balance"])

    after_cur = await db.execute(
        "SELECT COUNT(*) FROM portfolio_snapshots WHERE user_id='default'"
    )
    after = (await after_cur.fetchone())[0]
    assert after == before + 1, (
        f"trade should insert exactly 1 snapshot, got delta={after - before}"
    )

    # Most recent snapshot's total_value should equal cash + 1 * aapl_price
    import app.main as main

    aapl_price = main.state.price_cache.get_price("AAPL")
    cur = await db.execute(
        "SELECT total_value FROM portfolio_snapshots WHERE user_id='default' "
        "ORDER BY recorded_at DESC LIMIT 1"
    )
    row = await cur.fetchone()
    # row stores cents; convert via from_cents (imported at module top)
    assert from_cents(row["total_value"]) == pytest.approx(
        cash_after + aapl_price, abs=0.05
    )


# ---------------------------------------------------------------------------
# Lifespan wiring
# ---------------------------------------------------------------------------


async def test_lifespan_starts_and_stops_snapshot_loop(testing_env, fresh_db):
    """Lifespan startup creates state.snapshot_task; shutdown clears it.

    Note: the task object itself is bound to TestClient's internal event
    loop, not pytest-asyncio's test loop — so we only assert structural
    invariants (presence on entry, cleared on exit). The task's running
    state is verified indirectly via the DB count test.
    """
    from fastapi.testclient import TestClient

    import app.main as main
    from app.main import app

    assert main.state.snapshot_task is None
    assert main.state._snapshot_stop is None

    with TestClient(app):
        # Inside the context: lifespan startup has run.
        assert main.state.snapshot_task is not None
        assert main.state._snapshot_stop is not None
        # The stop event should NOT be set yet (loop is alive).
        assert not main.state._snapshot_stop.is_set()

    # After __exit__: lifespan shutdown has run.
    assert main.state.snapshot_task is None
    assert main.state._snapshot_stop is None
