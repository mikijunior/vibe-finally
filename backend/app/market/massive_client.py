"""Massive (Polygon.io) API client for real market data."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

try:  # Optional dependency: simulator-only runs should not require Massive.
    from massive import RESTClient as RESTClient
except ImportError:  # pragma: no cover - exercised when dependency is absent
    RESTClient = None  # type: ignore[assignment]

try:
    from massive.rest.models import SnapshotMarketType as SnapshotMarketType
except ImportError:  # pragma: no cover - exercised when dependency is absent
    SnapshotMarketType = None  # type: ignore[assignment]

from .cache import PriceCache
from .interface import MarketDataSource
from .tickers import normalize_ticker, normalize_tickers

logger = logging.getLogger(__name__)


class MassiveDataSource(MarketDataSource):
    """MarketDataSource backed by the Massive (Polygon.io) REST API.

    Polls all watched stock tickers in a single snapshot request, then writes
    normalized price updates into the shared PriceCache. The Massive package is
    optional until this source is actually started so the default simulator path
    works without real-market-data dependencies installed.
    """

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
    ) -> None:
        self._api_key = api_key
        self._cache = price_cache
        self._interval = poll_interval
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._client: Any | None = None

    async def start(self, tickers: list[str]) -> None:
        if self._task is not None and not self._task.done():
            raise RuntimeError("Massive market data source is already running")

        if RESTClient is None:
            raise RuntimeError(
                "Massive market data requested, but the 'massive' package is not installed. "
                "Install backend dependencies or unset MASSIVE_API_KEY to use the simulator."
            )

        self._client = RESTClient(api_key=self._api_key)
        self._tickers = normalize_tickers(tickers)

        await self._poll_once()

        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")
        logger.info(
            "Massive poller started: %d tickers, %.1fs interval",
            len(self._tickers),
            self._interval,
        )

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None
        logger.info("Massive poller stopped")

    async def add_ticker(self, ticker: str) -> None:
        ticker = normalize_ticker(ticker)
        if ticker and ticker not in self._tickers:
            self._tickers.append(ticker)
            logger.info("Massive: added ticker %s (will appear on next poll)", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        ticker = normalize_ticker(ticker)
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)
        logger.info("Massive: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _poll_loop(self) -> None:
        """Poll on interval. First poll already happened in start()."""
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        """Execute one poll cycle: fetch snapshots, update cache."""
        if not self._tickers or not self._client:
            return

        try:
            snapshots = await asyncio.to_thread(self._fetch_snapshots)
            processed = 0
            for snap in snapshots:
                try:
                    price = snap.last_trade.price
                    timestamp = snap.last_trade.timestamp / 1000.0
                    self._cache.update(
                        ticker=normalize_ticker(snap.ticker),
                        price=price,
                        timestamp=timestamp,
                    )
                    processed += 1
                except (AttributeError, TypeError) as e:
                    logger.warning(
                        "Skipping snapshot for %s: %s", getattr(snap, "ticker", "???"), e
                    )
            logger.debug("Massive poll: updated %d/%d tickers", processed, len(self._tickers))
        except Exception as e:
            logger.error("Massive poll failed: %s", e)

    def _fetch_snapshots(self) -> list[Any]:
        """Synchronous call to the Massive REST API. Runs in a thread."""
        if self._client is None:
            return []
        market_type = SnapshotMarketType.STOCKS if SnapshotMarketType is not None else "stocks"
        return self._client.get_snapshot_all(market_type=market_type, tickers=self._tickers)
