"""Background snapshot loop for portfolio_snapshots (SNAP-01).

Runs every ``interval_seconds``, computes total portfolio value (cash +
positions x live PriceCache prices), and inserts one row via
SnapshotRepository. The loop exits cleanly when ``stop_event`` is set or
when the task is cancelled.

Key invariants:

- ``asyncio.wait_for(stop_event.wait(), timeout=interval)`` bounds
  shutdown latency to <= one interval without busy-waiting.
- One failed iteration never kills the loop — wrap in try/except.
- Use ``PriceCache.get_price`` (returns ``float | None``) so the loop
  is compatible with both the live simulator and a fake cache in tests.
- Position math is performed in dollars throughout; cents conversion
  is handled inside ``SnapshotRepository.insert``.
"""
from __future__ import annotations

import asyncio
import logging

from app.db.repositories.position import PositionRepository
from app.db.repositories.snapshot import SnapshotRepository
from app.db.repositories.user import UserRepository
from app.market.cache import PriceCache

logger = logging.getLogger(__name__)


async def _compute_total_value(price_cache: PriceCache) -> float:
    """Compute total portfolio value: cash + sum(qty * price) across positions.

    Missing PriceCache prices contribute 0.0 (defensive — first tick of a
    newly-added ticker may not have arrived yet). Returns 0.0 if no user
    row exists yet (uninitialized DB).
    """
    user = await UserRepository().get()
    if user is None:
        return 0.0
    cash = float(user["cash_balance"])
    positions = await PositionRepository().get_all()
    equity = 0.0
    for pos in positions:
        price = price_cache.get_price(pos["ticker"])
        if price is not None:
            equity += pos["quantity"] * price
    return cash + equity


async def _snapshot_loop(
    price_cache: PriceCache, stop_event: asyncio.Event, interval: float
) -> None:
    """Inner loop body. Exits cleanly when ``stop_event`` is set."""
    while not stop_event.is_set():
        try:
            total = await _compute_total_value(price_cache)
            await SnapshotRepository().insert(total)
            logger.debug("snapshot recorded: total=%.2f", total)
        except Exception:
            logger.exception("snapshot loop iteration failed; continuing")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


def start_snapshot_loop(
    price_cache: PriceCache,
    stop_event: asyncio.Event,
    interval_seconds: float = 30.0,
) -> asyncio.Task:
    """Spawn the snapshot loop as a background asyncio task and return it.

    The task runs until ``stop_event`` is set or it is cancelled. Exceptions
    inside one iteration are logged and the loop continues on the next tick.
    """
    return asyncio.create_task(
        _snapshot_loop(price_cache, stop_event, interval_seconds),
        name="snapshot-loop",
    )
