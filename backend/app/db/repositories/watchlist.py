"""Watchlist repository for FinAlly database."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..connection import get_db

DEFAULT_USER_ID = "default"


class WatchlistRepository:
    """Repository for watchlist operations."""

    USER_ID = DEFAULT_USER_ID

    async def get_all(self) -> list[dict]:
        """Return all watchlist rows for the default user."""
        db = await get_db()
        async with db.execute(
            "SELECT id, ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at",
            (self.USER_ID,),
        ) as cursor:
            rows = [dict(row) async for row in cursor]
        return rows

    async def add(self, ticker: str) -> dict:
        """Add a ticker to the watchlist. Returns the created row."""
        db = await get_db()
        now = datetime.now(timezone.utc).isoformat()
        id_ = str(uuid.uuid4())
        await db.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (id_, self.USER_ID, ticker.upper(), now),
        )
        await db.commit()
        return {"id": id_, "user_id": self.USER_ID, "ticker": ticker.upper(), "added_at": now}

    async def remove(self, ticker: str) -> bool:
        """Remove a ticker from the watchlist. Returns True if removed."""
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM watchlist WHERE user_id = ? AND ticker = ?",
            (self.USER_ID, ticker.upper()),
        )
        await db.commit()
        return cursor.rowcount > 0

    async def exists(self, ticker: str) -> bool:
        """Return True if the ticker is in the watchlist."""
        db = await get_db()
        async with db.execute(
            "SELECT 1 FROM watchlist WHERE user_id = ? AND ticker = ? LIMIT 1",
            (self.USER_ID, ticker.upper()),
        ) as cursor:
            row = await cursor.fetchone()
        return row is not None
